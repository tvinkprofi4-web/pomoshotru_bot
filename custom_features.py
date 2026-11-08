"""
custom_features.py
Dynamic & Autonomous Custom Features & Extension Engine for AI for copil
Exclusively designed for Creator k3rnel (ID: 6363403785, @k3rnel8633)
"""
import os
import sys
import time
import logging
import html
import datetime
try:
    import pytz
except ImportError:
    pytz = None
import telebot
from telebot import types

logger = logging.getLogger(__name__)

# Creator & Developer Identity
K3RNEL_ID = 6363403785
K3RNEL_USERNAMES = {"k3rnel8633", "k3rnel", "rnel88", "auser7742"}
MRZENUYT_ID = 7758799391
MRZENUYT_USERNAMES = {"imnotrealqwq", "mrzenuyt"}

def is_creator(user_or_id):
    """Checks if given user or user_id is the bot creator k3rnel."""
    if user_or_id is None:
        return False
    if isinstance(user_or_id, int):
        return user_or_id == K3RNEL_ID
    uid = getattr(user_or_id, 'id', 0)
    if uid == K3RNEL_ID:
        return True
    uname = (getattr(user_or_id, 'username', '') or '').strip().lstrip('@').lower()
    return uname in K3RNEL_USERNAMES

def is_developer(user_or_id):
    """Checks if given user is bot creator or developer."""
    if is_creator(user_or_id):
        return True
    if isinstance(user_or_id, int):
        return user_or_id == MRZENUYT_ID
    uid = getattr(user_or_id, 'id', 0)
    if uid == MRZENUYT_ID:
        return True
    uname = (getattr(user_or_id, 'username', '') or '').strip().lstrip('@').lower()
    return uname in MRZENUYT_USERNAMES

# Registry of dynamically added commands and capabilities
DYNAMIC_COMMANDS = {}

def register_custom_features(bot, database=None, moderation=None, config=None):
    """
    Initializes and attaches dynamic commands without unused debug commands.
    """
    global DYNAMIC_COMMANDS
    DYNAMIC_COMMANDS.clear()

    try:
        # Command 1: /cache_stats (Fast cache statistics)
        def _cmd_cache_stats(message):
            if database:
                m_stats = database.user_modes_cache.get_stats()
                r_stats = database.response_cache.get_stats()
                s_stats = database.search_cache.get_stats()
                l_stats = database.get_learning_stats()
                text = (
                    f"💾 <b>Статистика In-Memory LRU Кэша:</b>\n\n"
                    f"🔹 <b>Кэш настроек/режимов:</b> {m_stats['size']}/{m_stats['max_size']} (Hits: {m_stats['hits']}, Ratio: {m_stats['hit_ratio_percent']}%)\n"
                    f"🔹 <b>Кэш ответов на запросы:</b> {r_stats['size']}/{r_stats['max_size']} (Hits: {r_stats['hits']}, Ratio: {r_stats['hit_ratio_percent']}%)\n"
                    f"🔹 <b>Кэш веб-поиска:</b> {s_stats['size']}/{s_stats['max_size']} (Hits: {s_stats['hits']}, Ratio: {s_stats['hit_ratio_percent']}%)\n\n"
                    f"🧠 <b>База самообучения:</b> {l_stats['total_unique_errors']} уникальных ошибок, {l_stats['total_occurrences']} исправлений."
                )
            else:
                text = "💾 Кэш активен."
            bot.reply_to(message, text, parse_mode="HTML")

        DYNAMIC_COMMANDS['cache_stats'] = _cmd_cache_stats
        DYNAMIC_COMMANDS['кэш'] = _cmd_cache_stats

        # Command 2: /time (World & City Time with Verboo AI fallback)
        CITY_OFFSETS = {
            'москва': (3, 'г. Москва (МСК)'), 'мск': (3, 'г. Москва (МСК)'), 'питер': (3, 'Санкт-Петербург'), 'спб': (3, 'Санкт-Петербург'),
            'калининград': (2, 'Калининград (MSK-1)'),
            'самара': (4, 'Самара (MSK+1)'), 'саратов': (4, 'Саратов (MSK+1)'), 'ижевск': (4, 'Ижевск (MSK+1)'),
            'екатеринбург': (5, 'г. Екатеринбург (MSK+2)'), 'екб': (5, 'г. Екатеринбург (MSK+2)'),
            'оренбург': (5, 'г. Оренбург (MSK+2)'), 'ореьунг': (5, 'г. Оренбург (MSK+2)'),
            'уфа': (5, 'г. Уфа (MSK+2)'), 'пермь': (5, 'г. Пермь (MSK+2)'), 'челябинск': (5, 'г. Челябинск (MSK+2)'), 'тюмень': (5, 'г. Тюмень (MSK+2)'),
            'омск': (6, 'г. Омск (MSK+3)'),
            'новосибирск': (7, 'г. Новосибирск (MSK+4)'), 'нск': (7, 'г. Новосибирск (MSK+4)'), 'красноярск': (7, 'г. Красноярск (MSK+4)'),
            'иркутск': (8, 'г. Иркутск (MSK+5)'),
            'якутск': (9, 'г. Якутск (MSK+6)'), 'владивосток': (10, 'г. Владивосток (MSK+7)'),
            'лондон': (1, 'г. Лондон (BST, UTC+1)'), 'париж': (2, 'г. Париж (CEST, UTC+2)'), 'берлин': (2, 'г. Берлин (CEST, UTC+2)'),
            'рим': (2, 'г. Рим (CEST, UTC+2)'), 'киев': (3, 'г. Киев (EEST, UTC+3)'), 'минск': (3, 'г. Минск (MSK, UTC+3)'),
            'стамбул': (3, 'г. Стамбул (TRT, UTC+3)'), 'дубай': (4, 'г. Дубай (GST, UTC+4)'),
            'ташкент': (5, 'г. Ташкент (UZT, UTC+5)'), 'астана': (5, 'г. Астана (UTC+5)'), 'алматы': (5, 'г. Алматы (UTC+5)'),
            'бангкок': (7, 'г. Бангкок (ICT, UTC+7)'), 'пекин': (8, 'г. Пекин (CST, UTC+8)'),
            'токио': (9, 'г. Токио (JST, UTC+9)'), 'сеул': (9, 'г. Сеул (KST, UTC+9)'),
            'нью-йорк': (-4, 'г. Нью-Йорк (EDT, UTC-4)'), 'вашингтон': (-4, 'г. Вашингтон (EDT, UTC-4)'),
            'лос-анджелес': (-7, 'г. Лос-Анджелес (PDT, UTC-7)')
        }

        def _cmd_time(message):
            import requests, re
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            raw_text = (message.text or message.caption or "").strip()
            q = raw_text.lower()
            
            # Check fast city lookup
            for word in re.findall(r'[a-zA-Zа-яА-ЯёЁ-]+', q):
                if word in ['время', 'time', 'скольк', 'щас', 'сейчас', 'в', 'во', 'на', 'по', 'какое', 'точный']:
                    continue
                w_stem = word.rstrip('еуаомях')
                for k, (offset, city_name) in CITY_OFFSETS.items():
                    if k == word or (len(w_stem) >= 3 and (k.startswith(w_stem) or w_stem in k)):
                        tz = datetime.timezone(datetime.timedelta(hours=offset))
                        c_time = now_utc.astimezone(tz)
                        diff = offset - 3
                        diff_str = f"+{diff}ч к МСК" if diff > 0 else (f"{diff}ч к МСК" if diff < 0 else "по Москве")
                        time_fmt = c_time.strftime("%d.%m.%Y %H:%M:%S")
                        bot.reply_to(message, f"🕒 <b>Текущее время в {city_name} ({diff_str}):</b>\n<code>{time_fmt}</code>", parse_mode="HTML")
                        return

            # Check if there is a city query not found in CITY_OFFSETS -> ask Verboo AI
            cleaned_query = re.sub(r"^[/!.]?(time|время)", "", raw_text, flags=re.IGNORECASE).strip()
            if cleaned_query and len(cleaned_query) > 2 and not any(cleaned_query.lower() == k for k in ['сейчас', 'щас', 'точный', 'мск', 'москва']):
                keys_pool = getattr(config, 'VERBOO_API_KEYS', []) if config else []
                if not keys_pool and getattr(config, 'VERBOO_API_KEY', None):
                    keys_pool = [config.VERBOO_API_KEY]
                if keys_pool:
                    k = keys_pool[0]
                    utc_str = now_utc.strftime('%H:%M:%S, %d.%m.%Y')
                    msk_str = (now_utc + datetime.timedelta(hours=3)).strftime('%H:%M:%S, %d.%m.%Y')
                    sys_prompt = f"Ты точный сервис времени. Сейчас по UTC: {utc_str}, а по Москве (MSK): {msk_str}. Назови точное текущее местное время в запрошенном месте: часовой пояс, смещение относительно Москвы и текущее время. Ответь кратко на русском."
                    try:
                        r = requests.post(
                            f"{getattr(config, 'VERBOO_API_BASE', 'https://code.verboo.ai/router/v1').rstrip('/')}/chat/completions",
                            headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
                            json={
                                "model": "deepseek-v4.1-flash",
                                "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": cleaned_query}],
                                "max_tokens": 300
                            },
                            timeout=8
                        )
                        if r.status_code == 200:
                            ans = r.json().get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                            if ans:
                                bot.reply_to(message, f"🕒 <b>Всемирное время (AI for copil):</b>\n\n{ans}", parse_mode="HTML")
                                return
                    except Exception as ve:
                        logger.warning(f"Verboo time error: {ve}")

            # Default Moscow Time
            moscow_tz = datetime.timezone(datetime.timedelta(hours=3))
            now_msk = now_utc.astimezone(moscow_tz)
            time_str = now_msk.strftime('%d.%m.%Y %H:%M:%S')
            bot.reply_to(
                message,
                f"🕒 <b>Текущее время (Москва, UTC+3):</b>\n<code>{time_str}</code>\n\n"
                f"💡 <i>Чтобы узнать время в другом городе, напиши:</i> <code>время в Оренбурге</code> <i>или</i> <code>/время Токио</code>",
                parse_mode="HTML"
            )

        DYNAMIC_COMMANDS['time'] = _cmd_time
        DYNAMIC_COMMANDS['время'] = _cmd_time

        # Register message handlers on bot instance
        if bot:
            @bot.message_handler(commands=['cache_stats', 'кэш'])
            def __h_cache(message):
                _cmd_cache_stats(message)

            @bot.message_handler(commands=['time', 'время'])
            def __h_time(message):
                _cmd_time(message)

        logger.info(f"Custom dynamic features successfully initialized! Registered commands: {list(DYNAMIC_COMMANDS.keys())}")
    except Exception as e:
        logger.error(f"Error initializing custom features: {e}")

def execute_dynamic_command(bot, message, cmd_name):
    """Executes a dynamic command if registered in DYNAMIC_COMMANDS."""
    cmd_clean = cmd_name.lower().lstrip('!./')
    if cmd_clean in DYNAMIC_COMMANDS:
        try:
            DYNAMIC_COMMANDS[cmd_clean](message)
            return True
        except Exception as e:
            logger.error(f"Error executing dynamic command {cmd_clean}: {e}", exc_info=True)
            bot.reply_to(message, f"⚠️ Ошибка выполнения команды <code>/{cmd_clean}</code>: {html.escape(str(e))}", parse_mode="HTML")
            return True
    return False