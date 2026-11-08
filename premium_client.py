import os
import asyncio
import threading
import logging
import time
import random
import inspect
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import ReactionEmoji, ReactionCustomEmoji
from telethon.tl.functions.account import UpdateStatusRequest
from telethon.errors import FloodWaitError
import config

logger = logging.getLogger(__name__)

_telethon_client = None
_telethon_loop = None
_telethon_thread = None
_is_ready = False
_my_user_id = 0
_my_has_premium = False
_lock = threading.Lock()
_deleted_listeners = []
_bot_target_listeners = []
_telethon_target_cooldowns = {}
_userbot_spam_cancels = {}

def get_my_id():
    """Returns Telegram user ID of authorized userbot account."""
    return _my_user_id

def get_telethon_client():
    return _telethon_client

def get_telethon_loop():
    return _telethon_loop

_always_online_active = True
_always_online_task = None
_always_online_lock = threading.Lock()

async def _always_online_loop():
    global _always_online_active, _is_ready
    from telethon.tl.functions.account import UpdateStatusRequest
    from telethon.tl.functions.updates import GetStateRequest
    from telethon.errors import FloodWaitError
    while True:
        try:
            is_active = get_always_online()
            _always_online_active = is_active
            if not is_active:
                await asyncio.sleep(5)
                continue
            if _telethon_client and _is_ready and _telethon_client.is_connected():
                try:
                    await _telethon_client(UpdateStatusRequest(offline=False))
                except FloodWaitError as fe:
                    logger.warning(f"Always Online FloodWait: {fe.seconds}s")
                    await asyncio.sleep(fe.seconds + 2)
                    continue
                except Exception as ue:
                    logger.debug(f"UpdateStatusRequest error in online loop: {ue}")
                try:
                    if _telethon_client.is_connected():
                        await _telethon_client(GetStateRequest())
                except FloodWaitError as fwe:
                    logger.warning(f"Always Online GetState FloodWait: {fwe.seconds}s")
                    await asyncio.sleep(fwe.seconds + 2)
                    continue
                except Exception as se:
                    logger.debug(f"GetStateRequest error in online loop: {se}")
            elif _telethon_client and not _is_ready:
                try:
                    if not _telethon_client.is_connected():
                        await _telethon_client.connect()
                    if await _telethon_client.is_user_authorized():
                        _is_ready = True
                        await _telethon_client(UpdateStatusRequest(offline=False))
                except Exception as re_err:
                    logger.debug(f"Auto-reconnect error in online loop: {re_err}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug(f"Error in telethon _always_online_loop: {e}")
        await asyncio.sleep(15)

def set_always_online(enabled: bool) -> bool:
    global _always_online_active, _always_online_task
    with _always_online_lock:
        _always_online_active = enabled
        try:
            import database
            database.set_app_setting("always_online", "1" if enabled else "0")
        except Exception:
            pass
        if _telethon_loop and _telethon_loop.is_running():
            if enabled:
                try:
                    if not _always_online_task or _always_online_task.done():
                        _always_online_task = _telethon_loop.create_task(_always_online_loop())
                except Exception as te:
                    logger.debug(f"Could not start always online task: {te}")
            async def _apply():
                try:
                    if _telethon_client and _is_ready and _telethon_client.is_connected():
                        from telethon.tl.functions.account import UpdateStatusRequest
                        await _telethon_client(UpdateStatusRequest(offline=not enabled))
                except Exception as e:
                    logger.debug(f"Could not update status: {e}")
            run_async_coro(_apply())
        return True

def get_always_online() -> bool:
    global _always_online_active
    try:
        import database
        val = database.get_app_setting("always_online", "1")
        return str(val).strip() in ["1", "true", "True"]
    except Exception:
        return _always_online_active

def is_always_online_active() -> bool:
    return _always_online_active and _is_ready

def is_always_online() -> bool:
    return get_always_online()

def has_premium() -> bool:
    global _my_has_premium
    return bool(_my_has_premium)

def send_premium_voice(chat_id, voice_bytes, reply_to=None):
    if not wait_until_ready(timeout=1.5):
        return False
    import io
    async def _send():
        chat_target = await _get_safe_target(chat_id)
        f = io.BytesIO(voice_bytes)
        f.name = "voice.ogg"
        return await _telethon_client.send_file(chat_target, f, voice_note=True, reply_to=reply_to)
    return run_async_coro(_send()) is not None

def is_premium_connected():
    return bool(_telethon_client and _is_ready and _telethon_client.is_connected())

def wait_until_ready(timeout=2.0):
    start = time.time()
    while time.time() - start < timeout:
        if _is_ready and _telethon_client and _telethon_client.is_connected():
            return True
        time.sleep(0.05)
    return False

def register_delete_listener(callback):
    """Registers callback(chat_id, deleted_ids) for deleted messages."""
    if callback not in _deleted_listeners:
        _deleted_listeners.append(callback)

def register_bot_target_listener(callback):
    """Registers callback(chat_id, sender_id, sender_uname, target_name, target_text, msg_id, is_bot) for auto-roasting targeted bots/users."""
    if callback not in _bot_target_listeners:
        _bot_target_listeners.append(callback)

async def _auto_delete_msg(chat_id, msg_id, delay=4.0):
    await asyncio.sleep(delay)
    try:
        await _telethon_client.delete_messages(chat_id, [msg_id])
    except Exception:
        pass

async def _get_safe_target(chat_id):
    if not _telethon_client:
        return chat_id
    try:
        return await _telethon_client.get_input_entity(chat_id)
    except Exception:
        try:
            await _telethon_client.get_dialogs(limit=50)
            return await _telethon_client.get_input_entity(chat_id)
        except Exception:
            return chat_id

async def _run_userbot_ladder(chat_id, custom_text="", reply_to_id=None):
    try:
        from troll_arsenal import TROLL_LADDER_PHRASES
        all_ladders = list(TROLL_LADDER_PHRASES)
        random.shuffle(all_ladders)
        idx = 0
        me = await _telethon_client.get_me()
        owner_handle = f"@{me.username}" if getattr(me, 'username', None) else (getattr(me, 'first_name', '') or "k3rnel")
        chat_target = await _get_safe_target(chat_id)

        is_single_volley = bool(custom_text)

        while not _userbot_spam_cancels.get(chat_id, False):
            if custom_text:
                phrase = custom_text
            else:
                phrase = all_ladders[idx % len(all_ladders)]
                idx += 1
                if idx % len(all_ladders) == 0:
                    random.shuffle(all_ladders)

            phrase = phrase.replace("{owner}", owner_handle)
            words = phrase.split()
            if not words:
                words = ["Соси", "Молча", "И", "Не", "Пищи"]

            for word in words:
                if _userbot_spam_cancels.get(chat_id, False):
                    return
                try:
                    if reply_to_id:
                        try:
                            await _telethon_client.send_message(chat_target, word, reply_to=reply_to_id)
                        except Exception:
                            await _telethon_client.send_message(chat_target, word)
                    else:
                        await _telethon_client.send_message(chat_target, word)
                    await asyncio.sleep(0.28)
                except Exception as e:
                    logger.warning(f"Error in telethon ladder send '{word}': {e}")
                    try:
                        chat_target = await _telethon_client.get_entity(chat_id)
                        await _telethon_client.send_message(chat_target, word)
                    except Exception as e2:
                        logger.debug(f"Fallback ladder send failed: {e2}")
                    await asyncio.sleep(0.5)

            if is_single_volley:
                break
            await asyncio.sleep(0.5)
    except Exception as le:
        logger.error(f"Error in _run_userbot_ladder task: {le}")

async def _run_userbot_aut_troll(chat_id, reply_to_id=None):
    try:
        from troll_arsenal import TROLL_PUNCHES, TROLL_TOXIC_TEMPLATES
        all_pool = list(TROLL_PUNCHES + TROLL_TOXIC_TEMPLATES)
        random.shuffle(all_pool)
        idx = 0
        me = await _telethon_client.get_me()
        owner_handle = f"@{me.username}" if getattr(me, 'username', None) else (getattr(me, 'first_name', '') or "k3rnel")
        chat_target = await _get_safe_target(chat_id)

        while not _userbot_spam_cancels.get(chat_id, False):
            raw_p = all_pool[idx % len(all_pool)]
            idx += 1
            if idx % len(all_pool) == 0:
                random.shuffle(all_pool)

            p = raw_p.replace("{owner}", owner_handle)
            try:
                if reply_to_id:
                    try:
                        await _telethon_client.send_message(chat_target, p, reply_to=reply_to_id)
                    except Exception:
                        await _telethon_client.send_message(chat_target, p)
                else:
                    await _telethon_client.send_message(chat_target, p)
                await asyncio.sleep(0.65)
            except Exception as e:
                logger.debug(f"Error in telethon aut_troll send: {e}")
                await asyncio.sleep(1.0)
    except Exception as te:
        logger.error(f"Error in _run_userbot_aut_troll task: {te}")

async def _run_userbot_spam(chat_id, text, count=10, reply_to_id=None):
    try:
        chat_target = await _get_safe_target(chat_id)
        for _ in range(count):
            if _userbot_spam_cancels.get(chat_id, False):
                return
            try:
                if reply_to_id:
                    try:
                        await _telethon_client.send_message(chat_target, text, reply_to=reply_to_id)
                    except Exception:
                        await _telethon_client.send_message(chat_target, text)
                else:
                    await _telethon_client.send_message(chat_target, text)
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.debug(f"Error in telethon spam send: {e}")
                await asyncio.sleep(0.6)
    except Exception as se:
        logger.error(f"Error in _run_userbot_spam task: {se}")

def _start_telethon_background():
    global _telethon_client, _telethon_loop, _is_ready
    from dotenv import load_dotenv
    load_dotenv()
    session_str = config.TELEGRAM_SESSION_STRING or os.getenv('TELEGRAM_SESSION_STRING', '')
    if not session_str or not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
        logger.warning("Telegram Userbot credentials not configured; Telethon userbot disabled.")
        return

    _telethon_loop = asyncio.new_event_loop()

    def _thread_target():
        asyncio.set_event_loop(_telethon_loop)

        async def _init_and_run():
            global _telethon_client, _is_ready, _my_user_id, _my_has_premium, _always_online_task
            while True:
                try:
                    logger.info("Initializing Telethon Userbot client...")
                    _telethon_client = TelegramClient(
                        StringSession(session_str),
                        int(config.TELEGRAM_API_ID),
                        str(config.TELEGRAM_API_HASH),
                        loop=_telethon_loop,
                        device_model="Desktop",
                        system_version="Windows 11 Pro",
                        app_version="5.8.3 x64"
                    )
                    await _telethon_client.connect()
                    if await _telethon_client.is_user_authorized():
                        me = await _telethon_client.get_me()
                        _my_user_id = getattr(me, 'id', 0)
                        _my_has_premium = getattr(me, 'premium', False)
                        _is_ready = True
                        logger.info(f"⭐️ Telegram Userbot authorized as: {getattr(me, 'first_name', '')} (@{getattr(me, 'username', 'N/A')}, ID: {_my_user_id}, Premium: {_my_has_premium})")

                        try:
                            if not _always_online_task or _always_online_task.done():
                                _always_online_task = _telethon_loop.create_task(_always_online_loop())
                                logger.info("⭐️ Always Online background presence task scheduled!")
                        except Exception as ae:
                            logger.debug(f"Could not restore always_online: {ae}")

                        @_telethon_client.on(events.MessageDeleted())
                        async def _on_deleted(event):
                            try:
                                c_id = event.chat_id
                                d_ids = event.deleted_ids or []
                                for cb in _deleted_listeners:
                                    try:
                                        cb(c_id, d_ids)
                                    except Exception as ce:
                                        logger.debug(f"Error in delete listener callback: {ce}")
                            except Exception as de:
                                logger.debug(f"Error in telethon MessageDeleted handler: {de}")

                        @_telethon_client.on(events.NewMessage())
                        async def _on_new_message(event):
                            try:
                                if not event.is_group and not event.is_channel:
                                    # Private chat check: instant purge if interlocutor is muted by secretary (.mute)
                                    if not event.out and event.chat_id:
                                        try:
                                            import database
                                            if database.is_secretary_chat_muted(_my_user_id, event.chat_id) or database.is_secretary_chat_muted(None, event.chat_id):
                                                await event.delete(revoke=True)
                                                return
                                        except Exception as _me:
                                            logger.debug(f"Telethon auto-delete muted message notice: {_me}")
                                    return
                                c_id = event.chat_id
                                s_id = event.sender_id
                                if not s_id or s_id == _my_user_id:
                                    return

                                sender = await event.get_sender()
                                s_uname = getattr(sender, 'username', '') or ''
                                is_bot = bool(getattr(sender, 'bot', False))

                                s_name = getattr(sender, 'first_name', '') or s_uname or f"ID:{s_id}"
                                import database
                                if database.is_chat_target(c_id, s_id, username=s_uname):
                                    now = time.time()
                                    ckey = (c_id, s_id)
                                    if now - _telethon_target_cooldowns.get(ckey, 0) < 3.0:
                                        return
                                    _telethon_target_cooldowns[ckey] = now

                                    t_text = event.raw_text or ""
                                    rep_text = ""
                                    if event.is_reply:
                                        try:
                                            q_msg = await event.get_reply_message()
                                            if q_msg and q_msg.raw_text:
                                                rep_text = q_msg.raw_text
                                        except Exception:
                                            pass

                                    from ai_roaster import generate_ai_target_roast
                                    punch = await asyncio.to_thread(generate_ai_target_roast, c_id, s_id, s_name, t_text, rep_text)
                                    try:
                                        await event.reply(punch)
                                    except Exception as re:
                                        logger.debug(f"Error in telethon direct target reply: {re}")
                            except Exception as nme:
                                logger.debug(f"Error in telethon NewMessage target handler: {nme}")

                        @_telethon_client.on(events.NewMessage(outgoing=True))
                        async def _on_userbot_outgoing(event):
                            try:
                                raw_text = (event.raw_text or "").strip()
                                if not (raw_text.startswith('.') or raw_text.startswith('!')):
                                    return

                                parts = raw_text.split()
                                first_w = parts[0].lower()
                                cmd = first_w.lstrip('.!').split('@')[0]
                                c_id = event.chat_id
                                rep_id = event.reply_to_msg_id

                                # Compound command normalization:
                                # e.g. .a troll, !a troll, .а тролль, .а тролл
                                if cmd in ["a", "а"] and len(parts) > 1 and parts[1].lower() in ["troll", "тролль", "тролл", "хам", "нейрохам"]:
                                    cmd = "a_troll"
                                    parts = [parts[0]] + parts[2:]

                                # e.g. .botoff / .ботофф / .boton / .ботон / .atrolloff / .onlyoff
                                if cmd in ["botoff", "ботофф", "бототкл"]:
                                    cmd = "bot"
                                    parts = [parts[0], "off"]
                                elif cmd in ["boton", "ботон", "ботвкл"]:
                                    cmd = "bot"
                                    parts = [parts[0], "on"]
                                elif cmd in ["onlyoff", "онлайнофф", "онлайноткл"]:
                                    cmd = "only"
                                    parts = [parts[0], "off"]
                                elif cmd in ["onlyon", "онлайнон", "онлайнвкл"]:
                                    cmd = "only"
                                    parts = [parts[0], "on"]
                                elif cmd in ["atrolloff", "атролльофф", "тролльофф", "троллофф"]:
                                    cmd = "a_troll"
                                    parts = [parts[0], "off"]

                                # 0.9 .only / .online / .онлайн / .вечныйонлайн / .вечный_онлайн (Always Online 24/7)
                                if cmd in ["only", "online", "онлайн", "вечный_онлайн", "вечныйонлайн", "always_online", "alwaysonline"]:
                                    arg = parts[1].lower() if len(parts) > 1 else ""
                                    try:
                                        await event.delete()
                                    except Exception:
                                        pass
                                    if arg in ["off", "0", "выкл", "stop", "disable", "откл", "офф", "стоп"]:
                                        new_state = False
                                    elif arg in ["status", "статус", "инфо", "info"]:
                                        new_state = is_always_online()
                                    else:
                                        new_state = True

                                    if arg not in ["status", "статус", "инфо", "info"]:
                                        set_always_online(new_state)
                                        import database
                                        if _my_user_id:
                                            database.set_user_always_online(_my_user_id, new_state)

                                    chat_target = await _get_safe_target(c_id)
                                    if new_state:
                                        status_msg = (
                                            "🟢 <b>ВЕЧНЫЙ ОНЛАЙН АКТИВИРОВАН (24/7)</b> ⚡\n"
                                            "━━━━━━━━━━━━━━━━━━━━━\n"
                                            "📡 <b>Статус:</b> 🟢 <i>Всегда в сети (Online)</i>\n"
                                            "⚙️ <b>Пинг присутствия:</b> MTProto Heartbeat (15s)\n"
                                            "💡 <i>Аккаунт активен даже при закрытом Telegram и выключенном телефоне!</i>\n"
                                            "━━━━━━━━━━━━━━━━━━━━━\n"
                                            "🛑 <i>Выключить: <code>.only off</code></i>"
                                        )
                                    else:
                                        status_msg = (
                                            "⚪️ <b>ВЕЧНЫЙ ОНЛАЙН ВЫКЛЮЧЕН</b> 💤\n"
                                            "━━━━━━━━━━━━━━━━━━━━━\n"
                                            "📡 <b>Статус:</b> ⚪️ <i>Стандартный (Telegram)</i>\n"
                                            "⚙️ <b>Фоновый пинг:</b> 🔴 Приостановлен\n"
                                            "━━━━━━━━━━━━━━━━━━━━━\n"
                                            "🟢 <i>Включить: <code>.only on</code></i>"
                                        )
                                    try:
                                        msg = await _telethon_client.send_message(chat_target, status_msg, parse_mode="html")
                                        asyncio.create_task(_auto_delete_msg(c_id, msg.id, 5.0))
                                    except Exception as se:
                                        logger.debug(f"Could not send .only response: {se}")
                                    return

                                # 0.95 .ping / .пинг / .pong
                                if cmd in ["ping", "пинг", "pong"]:
                                    import time
                                    t0 = time.time()
                                    try:
                                        await event.delete()
                                    except Exception:
                                        pass
                                    chat_target = await _get_safe_target(c_id)
                                    delta_ms = int((time.time() - t0) * 1000)
                                    msg = await _telethon_client.send_message(chat_target, f"🏓 <b>ПОНГ!</b> Скорость отклика: <code>{delta_ms} ms</code>\n🤖 <i>NullSecAI Userbot активен</i>", parse_mode="html")
                                    asyncio.create_task(_auto_delete_msg(c_id, msg.id, 4.0))
                                    return

                                # 0.98 .help / .хелп / .меню
                                if cmd in ["help", "хелп", "меню", "commands"]:
                                    try:
                                        await event.delete()
                                    except Exception:
                                        pass
                                    chat_target = await _get_safe_target(c_id)
                                    help_text = (
                                        "⚡ <b>NullSecAI Userbot / Секретарь — Команды:</b>\n"
                                        "━━━━━━━━━━━━━━━━━━━━━\n"
                                        "• <code>.only [on/off]</code> — Вечный онлайн 24/7 (Always Online)\n"
                                        "• <code>.bot [on/off]</code> — Автоответчик / Секретарь для чата\n"
                                        "• <code>.a_troll [@user / reply]</code> — Режим жесткого тролля (сброс: <code>.a_troll off</code>)\n"
                                        "• <code>.ladder [текст]</code> — Отправка лесенкой (стоп: <code>.ladder stop</code>)\n"
                                        "• <code>.aut_ladder</code> — Автоматическая бесконечная лесенка\n"
                                        "• <code>.spam [число] [текст]</code> — Быстрый спам сообщений\n"
                                        "• <code>.voice [текст]</code> — Озвучка текста голосовым сообщением\n"
                                        "• <code>.stop</code> — Экстренная остановка любого спама/лесенки\n"
                                        "• <code>.ping</code> — Проверка доступности бота"
                                    )
                                    msg = await _telethon_client.send_message(chat_target, help_text, parse_mode="html")
                                    asyncio.create_task(_auto_delete_msg(c_id, msg.id, 10.0))
                                    return

                                # 1. .stop / .стоп / .отмена
                                if cmd in ["stop", "стоп", "stop_spam", "stopspam", "stop_ladder", "stopladder", "stop_troll", "stoptroll", "laddstop", "ladderstop", "стопладдер", "стоплесенка", "отмена", "отменить"]:
                                    _userbot_spam_cancels[c_id] = True
                                    try:
                                        await event.delete()
                                    except Exception:
                                        pass
                                    return

                                # 2. .ladder / .лесенка / .ladd / .ладдер
                                if cmd in ["ladder", "лесенка", "ladd", "ладдер", "лесенку", "lad"]:
                                    if len(parts) > 1 and parts[1].lower() in ["stop", "стоп", "off", "офф", "0", "отмена"]:
                                        _userbot_spam_cancels[c_id] = True
                                        try:
                                            await event.delete()
                                        except Exception:
                                            pass
                                        return
                                    custom_t = raw_text.split(maxsplit=1)[1].strip() if len(parts) > 1 else ""
                                    try:
                                        await event.delete()
                                    except Exception:
                                        pass
                                    _userbot_spam_cancels[c_id] = False
                                    asyncio.create_task(_run_userbot_ladder(c_id, custom_t, rep_id))
                                    return

                                # 3. .aut_ladder / .автолесенка
                                if cmd in ["aut_ladder", "автолесенка", "авто_лесенка", "аутлесенка", "autladder"]:
                                    if len(parts) > 1 and parts[1].lower() in ["stop", "стоп", "off", "офф", "0", "отмена"]:
                                        _userbot_spam_cancels[c_id] = True
                                        try:
                                            await event.delete()
                                        except Exception:
                                            pass
                                        return
                                    custom_t = raw_text.split(maxsplit=1)[1].strip() if len(parts) > 1 else ""
                                    try:
                                        await event.delete()
                                    except Exception:
                                        pass
                                    _userbot_spam_cancels[c_id] = False
                                    asyncio.create_task(_run_userbot_ladder(c_id, custom_t, rep_id))
                                    return

                                # 4. .aut_troll / .аут_тролль
                                if cmd in ["aut_troll", "auttroll", "аут_тролль", "автотролль", "ауттролль", "авто_тролль", "аут_тролл", "автотролл"]:
                                    if len(parts) > 1 and parts[1].lower() in ["stop", "стоп", "off", "офф", "0", "отмена"]:
                                        _userbot_spam_cancels[c_id] = True
                                        try:
                                            await event.delete()
                                        except Exception:
                                            pass
                                        return
                                    try:
                                        await event.delete()
                                    except Exception:
                                        pass
                                    _userbot_spam_cancels[c_id] = False
                                    asyncio.create_task(_run_userbot_aut_troll(c_id, rep_id))
                                    return

                                # 5. .spam / .спам
                                if cmd in ["spam", "спам"]:
                                    count = 10
                                    s_text = "NullSecAI"
                                    if len(parts) > 1:
                                        if parts[1].isdigit():
                                            count = min(int(parts[1]), 100)
                                            s_text = " ".join(parts[2:]) if len(parts) > 2 else "NullSecAI"
                                        elif parts[-1].isdigit():
                                            count = min(int(parts[-1]), 100)
                                            s_text = " ".join(parts[1:-1])
                                        else:
                                            s_text = " ".join(parts[1:])
                                    try:
                                        await event.delete()
                                    except Exception:
                                        pass
                                    _userbot_spam_cancels[c_id] = False
                                    asyncio.create_task(_run_userbot_spam(c_id, s_text, count, rep_id))
                                    return

                                # 6. .bot on / .bot off / .бот офф / .бот вкл
                                if cmd in ["bot", "бот"]:
                                    arg = parts[1].lower() if len(parts) > 1 else ""
                                    try:
                                        await event.delete()
                                    except Exception:
                                        pass

                                    import database
                                    if arg in ["off", "0", "выкл", "stop", "disable", "откл", "сброс", "офф", "стоп"]:
                                        _userbot_spam_cancels[c_id] = True
                                        database.set_secretary_chat_enabled(_my_user_id, c_id, False)
                                        database.set_secretary_enabled(_my_user_id, False)
                                        database.set_user_mode(c_id, "default")
                                        database.set_secretary_chat_mode(_my_user_id, c_id, "assistant")
                                        try:
                                            targets = database.get_chat_targets(c_id)
                                            for t in targets:
                                                database.remove_chat_target(c_id, t.get("target_user_id"), username=t.get("target_username"))
                                        except Exception:
                                            pass
                                        
                                        chat_target = await _get_safe_target(c_id)
                                        msg = await _telethon_client.send_message(chat_target, "🛑 <b>Бот / Секретарь ВЫКЛЮЧЕН (.bot off) для этого чата!</b>\n🕊️ <i>Режим агрессии отключён, цели сброшены.</i>", parse_mode="html")
                                        asyncio.create_task(_auto_delete_msg(c_id, msg.id, 4.0))
                                    elif arg in ["on", "1", "вкл", "start", "enable", "он"]:
                                        database.set_secretary_chat_enabled(_my_user_id, c_id, True)
                                        database.set_secretary_enabled(_my_user_id, True)
                                        chat_target = await _get_safe_target(c_id)
                                        msg = await _telethon_client.send_message(chat_target, "✅ <b>AI-Секретарь ВКЛЮЧЕН (.bot on) для этого чата!</b>", parse_mode="html")
                                        asyncio.create_task(_auto_delete_msg(c_id, msg.id, 4.0))
                                    else:
                                        curr = database.is_secretary_chat_enabled(_my_user_id, c_id)
                                        new_st = not curr
                                        database.set_secretary_chat_enabled(_my_user_id, c_id, new_st)
                                        chat_target = await _get_safe_target(c_id)
                                        st_text = "ВКЛЮЧЕН ✅" if new_st else "ВЫКЛЮЧЕН 🛑"
                                        msg = await _telethon_client.send_message(chat_target, f"⚙️ <b>AI-Секретарь {st_text} для этого чата!</b>", parse_mode="html")
                                        asyncio.create_task(_auto_delete_msg(c_id, msg.id, 4.0))
                                    return

                                # 7. .a_troll / .atroll / .а_тролль / .атролль / .troll / .тролль / .хам / .нейрохам
                                                                # 8. .voice / .гс / .войс / .say / .скажи / .озвучить
                                if cmd in ["voice", "войс", "гс", "say", "скажи", "озвучить"]:
                                    text_to_speak = raw_text.split(maxsplit=1)[1].strip() if len(parts) > 1 else ""
                                    rep_msg = await event.get_reply_message() if rep_id else None
                                    if not text_to_speak and rep_msg:
                                        text_to_speak = rep_msg.raw_text or getattr(rep_msg, 'caption', '') or ""

                                    try:
                                        await event.delete()
                                    except Exception:
                                        pass

                                    if text_to_speak:
                                        import database
                                        from bot import generate_voice_bytes
                                        active_style = database.get_user_voice(_my_user_id) or "default"
                                        voice_bytes = await asyncio.to_thread(generate_voice_bytes, text_to_speak, style=active_style)
                                        if voice_bytes:
                                            chat_target = await _get_safe_target(c_id)
                                            import io
                                            f = io.BytesIO(voice_bytes)
                                            f.name = "voice.ogg"
                                            await _telethon_client.send_file(chat_target, f, voice_note=True, reply_to=rep_id)
                                    return

                                if cmd in ["a_troll", "atroll", "а_тролль", "атролль", "а_тролл", "атролл", "troll", "тролль", "тролл", "хам", "нейрохам"]:
                                    arg = parts[1].lower() if len(parts) > 1 else ""
                                    try:
                                        await event.delete()
                                    except Exception:
                                        pass

                                    import database
                                    if arg in ["off", "stop", "стоп", "0", "выкл", "откл", "офф"]:
                                        _userbot_spam_cancels[c_id] = True
                                        try:
                                            targets = database.get_chat_targets(c_id)
                                            for t in targets:
                                                database.remove_chat_target(c_id, t.get("target_user_id"), username=t.get("target_username"))
                                        except Exception:
                                            pass
                                        chat_target = await _get_safe_target(c_id)
                                        msg = await _telethon_client.send_message(chat_target, "🛑 <b>Режим тролля (.a_troll) ВЫКЛЮЧЕН! Цели сброшены.</b>", parse_mode="html")
                                        asyncio.create_task(_auto_delete_msg(c_id, msg.id, 4.0))
                                        return

                                    target_id = None
                                    target_name = None
                                    rep_msg = await event.get_reply_message() if rep_id else None
                                    if rep_msg:
                                        sender = await rep_msg.get_sender()
                                        if sender:
                                            target_id = sender.id
                                            target_name = getattr(sender, 'username', '') or getattr(sender, 'first_name', '')
                                    elif len(parts) > 1 and parts[1].startswith('@'):
                                        target_name = parts[1].lstrip('@')
                                        try:
                                            t_entity = await _telethon_client.get_entity(target_name)
                                            target_id = t_entity.id
                                        except Exception:
                                            target_id = - (abs(hash(target_name.lower())) % 900000000 + 100000000)

                                    if target_id or target_name:
                                        if target_id in [6363403785, 7758799391]:
                                            chat_target = await _get_safe_target(c_id)
                                            msg = await _telethon_client.send_message(chat_target, "👑 Создатели k3rnel и MrZenuyt обладают иммунитетом от троллинга.")
                                            asyncio.create_task(_auto_delete_msg(c_id, msg.id, 4.0))
                                            return

                                        database.add_chat_target(c_id, target_id or 0, target_username=target_name or "", added_by=_my_user_id)
                                        chat_target = await _get_safe_target(c_id)
                                        confirm = await _telethon_client.send_message(chat_target, f"🎯 <b>Цель взята на прицел (.a_troll):</b> @{target_name or target_id}\n😈 <i>Злой тролль активирован для этой цели!</i>", parse_mode="html")
                                        asyncio.create_task(_auto_delete_msg(c_id, confirm.id, 4.0))

                                        from ai_roaster import generate_ai_target_roast
                                        target_disp = target_name or "жертва"
                                        rep_content = (rep_msg.raw_text or "") if rep_msg else "ты взят на прицел"
                                        punch = await asyncio.to_thread(generate_ai_target_roast, c_id, target_id or 0, target_disp, rep_content, "")
                                        try:
                                            if rep_msg:
                                                await rep_msg.reply(punch)
                                            else:
                                                await _telethon_client.send_message(chat_target, punch)
                                        except Exception as pe:
                                            logger.debug(f"Direct punch failed: {pe}")
                                    else:
                                        chat_target = await _get_safe_target(c_id)
                                        msg = await _telethon_client.send_message(chat_target, "🎯 <b>Использование <code>.a_troll</code>:</b>\nОтветьте на сообщение жертвы (пользователя или бота) командой <code>.a_troll</code> или укажите <code>.a_troll @username</code>\n🛑 <i>Выключить: <code>.a_troll off</code></i>", parse_mode="html")
                                        asyncio.create_task(_auto_delete_msg(c_id, msg.id, 4.0))
                                    return

                            except Exception as oe:
                                logger.debug(f"Error in telethon outgoing userbot handler: {oe}")

                        try:
                            await _telethon_client.get_dialogs(limit=50)
                            logger.info("⭐️ Pre-cached recent dialogs in Telethon entity cache!")
                        except Exception as de_err:
                            logger.debug(f"Could not pre-cache dialogs: {de_err}")

                        await _telethon_client.run_until_disconnected()
                        logger.warning("⭐️ Telethon connection disconnected, auto-reconnecting in 3s...")
                        _is_ready = False
                        await asyncio.sleep(3)
                    else:
                        logger.warning("Telegram Userbot session is not authorized.")
                        _is_ready = False
                        await asyncio.sleep(4)
                except Exception as loop_e:
                    if "AuthKeyDuplicatedError" in str(loop_e) or "session" in str(loop_e).lower():
                        logger.warning(f"Telethon session revoked/duplicated: {loop_e}. Disconnecting and disabling Userbot thread.")
                        try:
                            if _telethon_client:
                                await _telethon_client.disconnect()
                        except Exception:
                            pass
                        _is_ready = False
                        return
                    else:
                        logger.warning(f"Telethon connection loop exception: {loop_e}, auto-reconnecting in 5s...")
                        _is_ready = False
                        await asyncio.sleep(5)

        _telethon_loop.create_task(_init_and_run())
        _telethon_loop.run_forever()

    _telethon_thread = threading.Thread(target=_thread_target, name="TelethonUserbotThread", daemon=True)
    _telethon_thread.start()

def init_premium_client():
    global _telethon_thread
    with _lock:
        if _telethon_thread is None or not _telethon_thread.is_alive():
            _start_telethon_background()

def run_async_coro(coro, timeout=10.0):
    if not _telethon_loop or not _telethon_loop.is_running():
        return None
    future = asyncio.run_coroutine_threadsafe(coro, _telethon_loop)
    try:
        return future.result(timeout=timeout)
    except Exception as e:
        logger.debug(f"Telethon task exception: {e}")
        return None

def send_premium_message(chat_id, text, reply_to=None, parse_mode='html', **kwargs):
    if not wait_until_ready(timeout=1.5):
        return False
    async def _send():
        chat_target = await _get_safe_target(chat_id)
        return await _telethon_client.send_message(chat_target, text, reply_to=reply_to, parse_mode=parse_mode)
    return run_async_coro(_send()) is not None

def edit_premium_message(chat_id, message_id, new_text, parse_mode='html', **kwargs):
    if not wait_until_ready(timeout=1.5):
        return False
    async def _edit():
        chat_target = await _get_safe_target(chat_id)
        return await _telethon_client.edit_message(chat_target, message_id, new_text, parse_mode=parse_mode)
    return run_async_coro(_edit()) is not None

def delete_premium_message(chat_id, message_id):
    if not wait_until_ready(timeout=1.5):
        return False
    async def _del():
        try:
            chat_target = await _get_safe_target(chat_id)
            mids = list(message_id) if isinstance(message_id, (list, tuple, set)) else [message_id]
            return await _telethon_client.delete_messages(chat_target, mids, revoke=True)
        except Exception as e:
            logger.warning(f"Telethon delete_message error in {chat_id}: {e}")
            return None
    return run_async_coro(_del()) is not None

def send_premium_file(chat_id, file, caption=None, reply_to=None):
    if not wait_until_ready(timeout=1.5):
        return False
    async def _send():
        chat_target = await _get_safe_target(chat_id)
        return await _telethon_client.send_file(chat_target, file, caption=caption, reply_to=reply_to)
    return run_async_coro(_send()) is not None

PREMIUM_REACTIONS = [
    5443038326535791479,
    5445284980970274641,
    5447644880824222055,
    5451996504946399320,
    5449774020963884877,
    5449774020963884878,
    5451877404412760677,
    5447410659102871184,
    5447410659102871185,
    5452040651002630013,
    5449830574937361817,
    5447410659102871186,
    5449622996944966601,
    5451877404412760678,
    5449830574937361818,
    5452140839687971761,
    5449774020963884879,
    5451996504946399321,
    5445284980970274642,
    5447644880824222056
]

def get_random_premium_emoji():
    return random.choice(PREMIUM_REACTIONS)

def auto_react_random_premium(chat_id, msg_id):
    if not config.TELEGRAM_SESSION_STRING:
        return
    def _bg_react():
        time.sleep(0.3)
        send_premium_reaction(chat_id, msg_id)
    threading.Thread(target=_bg_react, daemon=True).start()

def send_premium_reaction(chat_id, msg_id, custom_emoji_id_or_char=None):
    if not wait_until_ready(timeout=1.5):
        return False
    async def _react():
        try:
            target = custom_emoji_id_or_char or random.choice(PREMIUM_REACTIONS)
            reaction = ReactionCustomEmoji(document_id=int(target)) if (isinstance(target, int) or str(target).isdigit()) else ReactionEmoji(emoticon=str(target))
            chat_target = await _get_safe_target(chat_id)
            return await _telethon_client.send_reaction(chat_target, msg_id, reaction)
        except Exception as e:
            logger.debug(f"Telethon send_reaction error in {chat_id}: {e}")
            return None
    return run_async_coro(_react()) is not None

init_premium_client()
