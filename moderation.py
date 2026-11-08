import os
import json
import time
import datetime
import re
import html
import logging
from telebot import types

logger = logging.getLogger(__name__)

# ==========================================
# TELEGRAM PREMIUM ANIMATED CUSTOM EMOJIS (HTML <tg-emoji>)
# ==========================================

PE = {
    "fire": '<tg-emoji emoji-id="5449806834217014350">🔥</tg-emoji>',
    "crown": '<tg-emoji emoji-id="5879728293132902896">👑</tg-emoji>',
    "cool": '<tg-emoji emoji-id="5449543526951963635">😎</tg-emoji>',
    "robot": '<tg-emoji emoji-id="5431490770089560625">🤖</tg-emoji>',
    "lightning": '<tg-emoji emoji-id="5373066076558996568">⚡️</tg-emoji>',
    "rocket": '<tg-emoji emoji-id="5451973731117191734">🚀</tg-emoji>',
    "star": '<tg-emoji emoji-id="5408977655330517200">⭐</tg-emoji>',
    "diamond": '<tg-emoji emoji-id="5465283645788937267">💎</tg-emoji>',
    "devil": '<tg-emoji emoji-id="5451855744070602793">😈</tg-emoji>',
    "coin": '<tg-emoji emoji-id="5431416651838932108">💰</tg-emoji>',
    "trophy": '<tg-emoji emoji-id="5879728293132902896">🏆</tg-emoji>',
    "skull": '<tg-emoji emoji-id="5375603491697865684">💀</tg-emoji>',
    "thinking": '<tg-emoji emoji-id="5451653416751221349">🤔</tg-emoji>',
    "eyes": '<tg-emoji emoji-id="5449877069817204015">👀</tg-emoji>',
    "folder": '<tg-emoji emoji-id="5452040651002630013">📁</tg-emoji>',
    "shield": '<tg-emoji emoji-id="5451757823111219669">🛡</tg-emoji>',
    "tools": '<tg-emoji emoji-id="5449755500767890279">🛠</tg-emoji>',
    "briefcase": '<tg-emoji emoji-id="5452040651002630013">💼</tg-emoji>',
    "code": '<tg-emoji emoji-id="5451730296665821234">💻</tg-emoji>',
    "check": '<tg-emoji emoji-id="5451757823111219669">✅</tg-emoji>',
    "cross": '<tg-emoji emoji-id="5769353028104625479">❌</tg-emoji>',
    "game": '<tg-emoji emoji-id="5409125874651903587">🎮</tg-emoji>',
    "sparkles": '<tg-emoji emoji-id="5341441218746293443">✨</tg-emoji>',
    "dice": '<tg-emoji emoji-id="5409125874651903587">🎲</tg-emoji>',
    "heart": '<tg-emoji emoji-id="5449816407699116057">❤️</tg-emoji>',
    "flower": '<tg-emoji emoji-id="5449379656769754226">🌸</tg-emoji>',
    "ping": '<tg-emoji emoji-id="5373066076558996568">🏓</tg-emoji>',
    "warning": '<tg-emoji emoji-id="5449528855343680404">⚠️</tg-emoji>',
    "lock": '<tg-emoji emoji-id="5451757823111219669">🔒</tg-emoji>',
    "key": '<tg-emoji emoji-id="5229153645299245972">🔑</tg-emoji>',
    "bulb": '<tg-emoji emoji-id="5886300009707610149">💡</tg-emoji>',
    "user": '<tg-emoji emoji-id="5449543526951963635">👤</tg-emoji>',
    "search": '<tg-emoji emoji-id="5449877069817204015">🔍</tg-emoji>',
    "voice": '<tg-emoji emoji-id="5449627626706586889">🎙</tg-emoji>',
    "stats": '<tg-emoji emoji-id="5292195660601239780">📊</tg-emoji>',
    "dna": '<tg-emoji emoji-id="5291923604487808793">🧬</tg-emoji>',
    "server": '<tg-emoji emoji-id="5406901223326495466">🖥</tg-emoji>',
    "clock": '<tg-emoji emoji-id="5451653416751221349">⏳</tg-emoji>',
    "pin": '<tg-emoji emoji-id="5449877069817204015">📌</tg-emoji>',
    "target": '<tg-emoji emoji-id="5408977655330517200">🎯</tg-emoji>',
    "art": '<tg-emoji emoji-id="5341665785406308254">🎨</tg-emoji>',
    "money": '<tg-emoji emoji-id="5292006737874792240">💵</tg-emoji>',
    "gift": '<tg-emoji emoji-id="5449365015226240241">🎁</tg-emoji>',
    "card": '<tg-emoji emoji-id="5451996923940582949">💳</tg-emoji>',
    "shop": '<tg-emoji emoji-id="5193065010795911968">🛍</tg-emoji>',
    "masks": '<tg-emoji emoji-id="5451855744070602793">🎭</tg-emoji>',
    "pencil": '<tg-emoji emoji-id="5449392958283468480">📝</tg-emoji>',
    "finger_down": '<tg-emoji emoji-id="5449487649427444768">👇</tg-emoji>',
    "radio_on": '<tg-emoji emoji-id="5323787447165787608">🟢</tg-emoji>',
    "radio_off": '<tg-emoji emoji-id="5323423027780656841">🔴</tg-emoji>',
    "on": '<tg-emoji emoji-id="5323787447165787608">🟢</tg-emoji>',
    "off": '<tg-emoji emoji-id="5323423027780656841">🔴</tg-emoji>',
    "phone": '<tg-emoji emoji-id="5449696590996458029">📱</tg-emoji>',
    "book": '<tg-emoji emoji-id="5451933989784800831">📖</tg-emoji>',
    "wrench": '<tg-emoji emoji-id="5449755500767890279">🔧</tg-emoji>',
    "movie": '<tg-emoji emoji-id="5406901223326495466">🎬</tg-emoji>',
    "music": '<tg-emoji emoji-id="5449627626706586889">🎵</tg-emoji>',
    "globe": '<tg-emoji emoji-id="5296385250874638951">🌐</tg-emoji>',
    "broom": '<tg-emoji emoji-id="5451768135327697004">🧹</tg-emoji>',
    "brain": '<tg-emoji emoji-id="5451730296665821234">🧠</tg-emoji>',
    "stop": '<tg-emoji emoji-id="5449528855343680404">⛔️</tg-emoji>',
    "package": '<tg-emoji emoji-id="5825630727613456050">📦</tg-emoji>',
    "swords": '<tg-emoji emoji-id="5449817339707019730">⚔️</tg-emoji>',
    "gun": '<tg-emoji emoji-id="5449527433709504916">🔫</tg-emoji>',
    "bomb": '<tg-emoji emoji-id="5449569945295805790">💣</tg-emoji>',
    "ninja": '<tg-emoji emoji-id="5785307414270058166">🥷</tg-emoji>',
    "hammer": '<tg-emoji emoji-id="5888940358032695118">🔨</tg-emoji>',
    "gear": '<tg-emoji emoji-id="5769531264952442902">⚙️</tg-emoji>',
    "swear": '<tg-emoji emoji-id="5449499121285090000">🤬</tg-emoji>',
    "nsfw": '<tg-emoji emoji-id="5875452644599795072">🔞</tg-emoji>',
    "link": '<tg-emoji emoji-id="5828076522509967259">🔗</tg-emoji>',
    "scale": '<tg-emoji emoji-id="5449525561103772382">⚖️</tg-emoji>',
    "smile": '<tg-emoji emoji-id="5449552829851125905">😃</tg-emoji>',
    "love": '<tg-emoji emoji-id="5449888288271781300">😍</tg-emoji>',
    "sad": '<tg-emoji emoji-id="5449834833108816153">😔</tg-emoji>',
    "angry": '<tg-emoji emoji-id="5452031287973921510">😠</tg-emoji>',
    "kiss": '<tg-emoji emoji-id="5449790315772791446">😘</tg-emoji>'
}

def pe(key, default=""):
    """Returns Telegram Premium custom animated emoji tag with fallback."""
    return PE.get(key, default or key)

def pe_id(key):
    """Returns Telegram Premium custom animated emoji ID for InlineKeyboardButton icon_custom_emoji_id."""
    val = PE.get(key, "")
    m = re.search(r'emoji-id="(\d+)"', val)
    return m.group(1) if m else None

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "moderation_data.json")

def load_db():
    data = None
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading {DB_PATH}: {e}")

    # Fallback to SQLite if JSON file is missing or has no chats
    if not data or not data.get("chats"):
        try:
            import database
            sqlite_chats = database.get_all_chat_moderation_configs()
            if sqlite_chats:
                data = {"chats": sqlite_chats}
                try:
                    with open(DB_PATH, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                return data
        except Exception as se:
            logger.debug(f"SQLite load_db fallback notice: {se}")

    if not data or not isinstance(data, dict):
        data = {"chats": {}}
    return data

def save_db(data):
    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving {DB_PATH}: {e}")

    # Mirror into SQLite chat_moderation_config and persistent backup
    try:
        import database
        for cid, c_data in data.get("chats", {}).items():
            database.save_chat_moderation_config(cid, c_data)
        database.save_persistent_backup(force=False)
    except Exception as se:
        logger.debug(f"SQLite mirror notice in save_db: {se}")

    # Fast-sync to GitHub data-sync branch within 3 seconds
    try:
        import db_sync
        db_sync.trigger_fast_sync(delay_sec=3.0)
    except Exception:
        pass

def get_chat_data(chat_id, chat_title=""):
    db = load_db()
    cid = str(chat_id)
    if cid not in db["chats"]:
        # Check if SQLite has this chat config first
        try:
            import database
            c_cfg = database.get_chat_moderation_config(chat_id)
            if c_cfg and isinstance(c_cfg, dict):
                db["chats"][cid] = c_cfg
                save_db(db)
                return db["chats"][cid]
        except Exception:
            pass

        db["chats"][cid] = {
            "title": chat_title,
            "owner_id": None,
            "owner_name": "",
            "owner_username": "",
            "admins": {},
            "moders": {},
            "warns": {},
            "rules": "📌 *Правила чата пока не установлены.*\nИспользуйте команду `/setrules [текст]` для их создания.",
            "rules_buttons": []
        }
        save_db(db)
    return db["chats"][cid]

def update_chat_data(chat_id, chat_data):
    db = load_db()
    db["chats"][str(chat_id)] = chat_data
    save_db(db)

def register_user_info(chat_id, user):
    """Caches user basic info in chat database for mention resolution and syncs to SQLite."""
    if not user or getattr(user, "is_bot", False):
        return
    db = load_db()
    cid = str(chat_id)
    if cid not in db["chats"]:
        get_chat_data(chat_id)
        db = load_db()
    
    if "users" not in db["chats"][cid]:
        db["chats"][cid]["users"] = {}
    
    name = (getattr(user, "first_name", "") or "") + (" " + getattr(user, "last_name", "") if getattr(user, "last_name", None) else "")
    db["chats"][cid]["users"][str(user.id)] = {
        "id": user.id,
        "name": name.strip() or f"id_{user.id}",
        "username": getattr(user, "username", "") or ""
    }
    save_db(db)
    
    try:
        import database
        database.register_user(user)
    except Exception:
        pass

def find_user_by_mention(chat_id, mention_text):
    """Finds user_id and info from @username or user_id in database cache, SQLite, and across chats."""
    if not mention_text:
        return None, None
    clean = str(mention_text).replace("@", "").strip()
    clean_lower = clean.lower()

    # 1. Creator & Developer alias resolution
    if clean_lower in ("k3rnel8633", "k3rnel", "rnel88", "auser7742", "rnel"):
        return 6363403785, {"id": 6363403785, "name": "k3rnel", "username": "rnel88"}
    if clean_lower in ("imnotrealqwq", "mrzenuyt", "zenuyt", "zenu"):
        return 7758799391, {"id": 7758799391, "name": "MrZenuyt", "username": "imnotrealqwq"}

    db = load_db()
    cid = str(chat_id)
    users = db.get("chats", {}).get(cid, {}).get("users", {})
    
    # 2. Check numeric ID
    if clean.isdigit():
        uid = int(clean)
        if str(uid) in users:
            return uid, users[str(uid)]
        try:
            import database
            u_db = database.get_user_by_username_or_id(uid)
            if u_db:
                uname = (u_db.get("first_name") or "") + (" " + u_db.get("last_name") if u_db.get("last_name") else "")
                return uid, {"id": uid, "name": uname.strip() or f"id_{uid}", "username": u_db.get("username") or ""}
        except Exception:
            pass
        return uid, {"id": uid, "name": f"id_{uid}", "username": ""}
    
    # 3. Check username in current chat
    for uid_str, u in users.items():
        if u.get("username", "").lower() == clean_lower:
            return int(uid_str), u

    # 4. Check SQLite database (users, sniffer_messages)
    try:
        import database
        u_db = database.get_user_by_username_or_id(clean)
        if u_db and u_db.get("user_id"):
            uid = int(u_db["user_id"])
            uname = (u_db.get("first_name") or "") + (" " + u_db.get("last_name") if u_db.get("last_name") else "")
            return uid, {"id": uid, "name": uname.strip() or f"@{clean}", "username": u_db.get("username") or clean}
    except Exception:
        pass

    # 5. Check across all other chats in moderation database
    for c_id, c_data in db.get("chats", {}).items():
        for uid_str, u in c_data.get("users", {}).items():
            if u.get("username", "").lower() == clean_lower:
                return int(uid_str), u
            
    return None, None

def parse_time_duration(time_str):
    """
    Parses time strings like '10m', '2h', '1d', '7d', '1w', '1mo', '15м', '2ч', '1д', '1н', 'навсегда'.
    Returns (seconds, human_readable_ru).
    """
    if not time_str:
        return None, None
        
    s = str(time_str).strip().lower()
    if s in ["навсегда", "forever", "0", "вечно", "perm", "permanent", "бессрочно"]:
        return None, "Навсегда"
    
    # Match patterns like: 10m, 10мин, 10минут, 2h, 2ч, 2часа, 1d, 1д, 1день, 7дней, 1w, 1н, 1нед, 1mo, 1мес
    pattern = r"^(\d+)\s*([a-zA-Zа-яА-ЯёЁ]*)$"
    match = re.match(pattern, s)
    if not match:
        return None, None
    
    val = int(match.group(1))
    unit = match.group(2).lower()
    
    if unit in ["s", "sec", "secs", "second", "seconds", "с", "сек", "секунд", "секунды", ""]:
        # enforce 30s minimum for Telegram temporary restrictions
        sec = max(30, val)
        txt = f"{val} сек."
    elif unit in ["m", "min", "mins", "minute", "minutes", "м", "мин", "минут", "минуты", "минута"]:
        sec = val * 60
        txt = f"{val} мин."
    elif unit in ["h", "hr", "hrs", "hour", "hours", "ч", "час", "часа", "часов"]:
        sec = val * 3600
        txt = f"{val} ч."
    elif unit in ["d", "day", "days", "д", "дн", "день", "дня", "дней"]:
        sec = val * 86400
        txt = f"{val} дн."
    elif unit in ["w", "wk", "week", "weeks", "н", "нед", "неделя", "недели", "недель"]:
        sec = val * 86400 * 7
        txt = f"{val} нед."
    elif unit in ["mo", "month", "months", "мес", "месяц", "месяца", "месяцев"]:
        sec = val * 86400 * 30
        txt = f"{val} мес."
    else:
        return None, None
        
    return sec, txt

def get_role_title(role_lvl, is_creator=False):
    """Returns human-readable role badge."""
    if is_creator:
        return "👑 Создатель (k3rnel)"
    if role_lvl == 3:
        return "👑 Владелец"
    if role_lvl == 2:
        return "🛡 Администратор"
    if role_lvl == 1:
        return "⚔️ Модератор"
    return "👤 Участник"

def get_user_role(bot, chat_id, user_id):
    """
    Returns role name ('owner', 'admin', 'moder', 'member') and role level:
    owner: 3, admin: 2, moder: 1, member: 0
    """
    chat_data = get_chat_data(chat_id)
    uid_str = str(user_id)
    
    # 1. Check local DB explicit owner
    if chat_data.get("owner_id") == user_id:
        return "owner", 3
        
    # 2. Check Telegram chat status
    try:
        member = bot.get_chat_member(chat_id, user_id)
        if member.status == "creator":
            if chat_data.get("owner_id") != user_id:
                name = (member.user.first_name or "") + (" " + member.user.last_name if member.user.last_name else "")
                chat_data["owner_id"] = user_id
                chat_data["owner_name"] = name.strip()
                chat_data["owner_username"] = member.user.username or ""
                update_chat_data(chat_id, chat_data)
            return "owner", 3
        elif member.status == "administrator":
            return "admin", 2
    except Exception as e:
        logger.debug(f"get_chat_member check failed: {e}")
        
    # 3. Check DB Admin
    if uid_str in chat_data.get("admins", {}):
        return "admin", 2
        
    # 4. Check DB Moder
    if uid_str in chat_data.get("moders", {}):
        return "moder", 1
        
    # 5. Check Custom Staff Roles in DB
    custom_roles = chat_data.get("custom_roles", {})
    highest_role = None
    highest_lvl = 0
    for r_key, r_info in custom_roles.items():
        if uid_str in r_info.get("members", {}):
            lvl = int(r_info.get("role_lvl", 1))
            rights = r_info.get("rights", "moder")
            if lvl > highest_lvl:
                highest_lvl = lvl
                highest_role = rights
    if highest_role:
        return highest_role, highest_lvl
        
    return "member", 0

def get_user_custom_role_title(chat_id, user_id):
    """Returns custom role title, rights and level if user is in a custom role."""
    chat_data = get_chat_data(chat_id)
    uid_str = str(user_id)
    custom_roles = chat_data.get("custom_roles", {})
    for r_key, r_info in custom_roles.items():
        if uid_str in r_info.get("members", {}):
            return r_info.get("title", ""), r_info.get("rights", "moder"), int(r_info.get("role_lvl", 1))
    return None, None, None

def check_user_punishment_status(bot, chat_id, user_id):
    """
    Checks real-time Telegram chat member punishment status.
    Returns:
      'banned' - if member.status == 'kicked'
      'muted' - if member.status == 'restricted' and (not can_send_messages)
      'none' - if member.status in ['creator', 'administrator', 'member'] (no restrictions)
      'left' - if member.status == 'left' (not in chat, not banned)
      'unknown' - on error / not found
    """
    if not bot or not chat_id or not user_id:
        return "unknown"
    try:
        member = bot.get_chat_member(chat_id, user_id)
        if member.status == "kicked":
            return "banned"
        elif member.status == "restricted":
            can_send = getattr(member, "can_send_messages", True)
            if not can_send:
                return "muted"
            return "none"
        elif member.status in ["creator", "administrator", "member"]:
            return "none"
        elif member.status == "left":
            return "left"
        return "none"
    except Exception as e:
        err_msg = str(e).lower()
        if "user not found" in err_msg or "participant" in err_msg or "chat not found" in err_msg:
            return "left"
        return "unknown"

def is_user_moderator(chat_id, user_id, is_creator=False, bot=None):
    """Checks if a user is a moderator, administrator, owner, or bot creator."""
    if is_creator:
        return True
    if not chat_id or not user_id:
        return False
    if bot:
        try:
            _, lvl = get_user_role(bot, chat_id, user_id)
            return lvl >= 1
        except Exception:
            pass
    chat_data = get_chat_data(chat_id)
    if chat_data.get("owner_id") == user_id:
        return True
    uid_str = str(user_id)
    if uid_str in chat_data.get("admins", {}) or uid_str in chat_data.get("moders", {}):
        return True
    return False

def format_user_mention(user_id, name, username=None):
    if username:
        return f"@{html.escape(username.replace('@', ''))}"
    clean_name = html.escape((name or f"id_{user_id}").strip())
    try:
        if user_id and int(user_id) < 0:
            return f"📢 <b>{clean_name}</b>"
    except Exception:
        pass
    return f'<a href="tg://user?id={user_id}">{clean_name}</a>'

def format_user_detailed_info(user_id, name, username=None, role_title=None):
    """
    Returns HTML string like:
    <a href="tg://user?id=123456">Имя</a> (@username | ID: <code>123456</code> | Ранг: <b>Администратор</b>)
    """
    clean_name = html.escape((name or f"id_{user_id}").strip()) or f"id_{user_id}"
    is_neg = False
    try:
        if user_id and int(user_id) < 0:
            is_neg = True
    except Exception:
        pass
    if is_neg:
        mention = f"📢 <b>{clean_name}</b>"
    else:
        mention = f'<a href="tg://user?id={user_id}">{clean_name}</a>'
    
    details = []
    if username:
        clean_user = html.escape(username.replace("@", "").strip())
        details.append(f"@{clean_user}")
    details.append(f"ID: <code>{user_id}</code>")
    if role_title:
        details.append(f"Ранг: <b>{html.escape(role_title)}</b>")
        
    details_str = " | ".join(details)
    return f"{mention} ({details_str})"

def format_expiry_datetime(until_ts):
    """
    Formats expiration timestamp into Russian date and time string:
    '16.09.2026 в 11:30 (МСК)' or 'Бессрочно (Навсегда)'.
    """
    if not until_ts or until_ts == 0:
        return "Бессрочно (Навсегда)"
    try:
        # Moscow Time (UTC+3)
        tz_msk = datetime.timezone(datetime.timedelta(hours=3))
        dt = datetime.datetime.fromtimestamp(until_ts, tz=tz_msk)
        return dt.strftime("%d.%m.%Y в %H:%M (МСК)")
    except Exception:
        return None

def format_punishment_card(action_type, target_info, issuer_info, duration_text=None, reason="Не указана", extra=None):
    """
    Formats standard stylish Telegram announcement card with verified Premium custom emojis and HTML.
    action_type: 'ban', 'unban', 'mute', 'unmute', 'kick', 'warn', 'unwarn', 'auto_mute_warn', 'promote', 'demote'
    """
    target_id = target_info.get("id")
    target_name = target_info.get("name")
    target_user = target_info.get("username")
    
    issuer_id = issuer_info.get("id")
    issuer_name = issuer_info.get("name")
    issuer_user = issuer_info.get("username")
    issuer_role = issuer_info.get("role_title")
    
    target_formatted = format_user_detailed_info(target_id, target_name, target_user)
    
    if action_type == 'auto_mute_warn':
        issuer_formatted = f"{PE['robot']} <b>Система защиты (Авто-модерация)</b>"
    else:
        issuer_formatted = format_user_detailed_info(issuer_id, issuer_name, issuer_user, role_title=issuer_role)
        
    clean_reason = html.escape((reason or "Не указана").strip())
    if not clean_reason:
        clean_reason = "Не указана"

    div_t = "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓"
    div_m = "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫"
    div_b = "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
    
    if action_type == 'ban':
        dur_str = duration_text or "Навсегда"
        until_ts = extra.get("until_ts") if extra else None
        expiry_str = format_expiry_datetime(until_ts) if until_ts else ("Бессрочно (Навсегда)" if dur_str == "Навсегда" else None)
        
        lines = [
            div_t,
            f"┃ {PE['skull']} <b>ТОТАЛЬНЫЙ БАН: ПОПУЩЕН И ВЫКИНУТ</b>",
            div_m,
            f"┃ 👤 <b>Нарушитель:</b> {target_formatted}",
            f"┃ 🛡 <b>Модератор:</b> {issuer_formatted}",
            f"┃ ⏱ <b>Срок бана:</b> <code>{html.escape(dur_str)}</code>"
        ]
        if expiry_str:
            lines.append(f"┃ ⏳ <b>Окончание:</b> <code>{html.escape(expiry_str)}</code>")
        lines.extend([
            f"┃ 📝 <b>Причина:</b> <i>{clean_reason}</i>",
            f"┃ 🚫 <i>Доступ в этот чат заблокирован.</i>",
            div_b
        ])
    elif action_type == 'unban':
        lines = [
            div_t,
            f"┃ {PE['check']} <b>ПОМИЛОВАНИЕ: РАЗБАНЕН В ЧАТЕ</b>",
            div_m,
            f"┃ 👤 <b>Пользователь:</b> {target_formatted}",
            f"┃ 🛡 <b>Разбанил:</b> {issuer_formatted}",
            f"┃ 🕊 <i>Блокировка снята, соблюдай правила.</i>",
            div_b
        ]
    elif action_type == 'mute':
        dur_str = duration_text or "10 мин."
        until_ts = extra.get("until_ts") if extra else None
        expiry_str = format_expiry_datetime(until_ts) if until_ts else None
        
        lines = [
            div_t,
            f"┃ {PE['lock']} <b>ЗАКРЫТИЕ РТА: ВЫДАН МУТ</b>",
            div_m,
            f"┃ 👤 <b>Нарушитель:</b> {target_formatted}",
            f"┃ 🛡 <b>Заткнул:</b> {issuer_formatted}",
            f"┃ ⏱ <b>Длительность:</b> <code>{html.escape(dur_str)}</code>"
        ]
        if expiry_str:
            lines.append(f"┃ ⏳ <b>Окончание:</b> <code>{html.escape(expiry_str)}</code>")
        lines.extend([
            f"┃ 📝 <b>Причина:</b> <i>{clean_reason}</i>",
            f"┃ 🤐 <i>Право голоса отключено. Сиди и читай молча.</i>",
            div_b
        ])
    elif action_type == 'unmute':
        lines = [
            div_t,
            f"┃ {PE['voice']} <b>СНЯТИЕ МУТА: ГОЛОС ВОЗВРАЩЁН</b>",
            div_m,
            f"┃ 👤 <b>Пользователь:</b> {target_formatted}",
            f"┃ 🛡 <b>Размутил:</b> {issuer_formatted}",
            f"┃ 🗣 <i>Ограничения на отправку сообщений сняты.</i>",
            div_b
        ]
    elif action_type == 'kick':
        lines = [
            div_t,
            f"┃ {PE['stop']} <b>ПЕНДЕЛЬ: ВЫШВЫРНУТ ИЗ ЧАТА</b>",
            div_m,
            f"┃ 👤 <b>Нарушитель:</b> {target_formatted}",
            f"┃ 🛡 <b>Выгнал:</b> {issuer_formatted}",
            f"┃ 📝 <b>Причина:</b> <i>{clean_reason}</i>",
            f"┃ 🚪 <i>Участник исключён из беседы.</i>",
            div_b
        ]
    elif action_type == 'warn':
        curr_warns = extra.get("warns", 1) if extra else 1
        max_warns = extra.get("max_warns", 3) if extra else 3
        lines = [
            div_t,
            f"┃ {PE['warning']} <b>ОФИЦИАЛЬНОЕ ПРЕДУПРЕЖДЕНИЕ [{curr_warns}/{max_warns}]</b>",
            div_m,
            f"┃ 👤 <b>Нарушитель:</b> {target_formatted}",
            f"┃ 🛡 <b>Выдал:</b> {issuer_formatted}",
            f"┃ ⚠️ <b>Лимит нарушений:</b> <code>[{curr_warns}/{max_warns}]</code>",
            f"┃ 📝 <b>Причина:</b> <i>{clean_reason}</i>",
            f"┃ ⚠️ <i>При достижении 3/3 варнов последует автоматический мут.</i>",
            div_b
        ]
    elif action_type == 'auto_mute_warn':
        dur_str = duration_text or "24 часа"
        until_ts = extra.get("until_ts") if extra else None
        expiry_str = format_expiry_datetime(until_ts) if until_ts else None
        lines = [
            div_t,
            f"┃ {PE['bomb']} <b>КРИТИЧЕСКИЙ ЛИМИТ: АВТО-МУТ 3/3 ВАРНОВ</b>",
            div_m,
            f"┃ 👤 <b>Нарушитель:</b> {target_formatted}",
            f"┃ 🤖 <b>Система:</b> Авто-наказание за 3 предупреждения",
            f"┃ ⏱ <b>Срок мута:</b> <code>{html.escape(dur_str)}</code>"
        ]
        if expiry_str:
            lines.append(f"┃ ⏳ <b>Окончание:</b> <code>{html.escape(expiry_str)}</code>")
        lines.extend([
            f"┃ ⚠️ <b>Варны:</b> <code>[3/3]</code> <i>(сброшены на 0)</i>",
            f"┃ 📝 <b>Причина:</b> <i>{clean_reason}</i>",
            f"┃ 🤐 <i>Лимит терпения исчерпан. Рот закрыт на 24 часа.</i>",
            div_b
        ])
    elif action_type == 'unwarn':
        curr_warns = extra.get("warns", 0) if extra else 0
        max_warns = extra.get("max_warns", 3) if extra else 3
        lines = [
            div_t,
            f"┃ {PE['check']} <b>СНЯТИЕ ПРЕДУПРЕЖДЕНИЯ (РАЗВАРН)</b>",
            div_m,
            f"┃ 👤 <b>Пользователь:</b> {target_formatted}",
            f"┃ 🛡 <b>Снял:</b> {issuer_formatted}",
            f"┃ 📊 <b>Осталось варнов:</b> <code>[{curr_warns}/{max_warns}]</code>",
            div_b
        ]
    elif action_type == 'promote':
        role_assigned = extra.get("role_title", "Модератор") if extra else "Модератор"
        lines = [
            div_t,
            f"┃ {PE['crown']} <b>НАЗНАЧЕНИЕ В ПЕРСОНАЛ</b>",
            div_m,
            f"┃ {PE['user']} <b>Пользователь:</b> {target_formatted}",
            f"┃ {PE['shield']} <b>Назначил:</b> {issuer_formatted}",
            f"┃ {PE['trophy']} <b>Должность:</b> <b>{html.escape(role_assigned)}</b>",
            div_b
        ]
    elif action_type == 'demote':
        lines = [
            div_t,
            f"┃ {PE['cross']} <b>СНЯТ С ДОЛЖНОСТИ / ПОПУЩЕН</b>",
            div_m,
            f"┃ {PE['user']} <b>Пользователь:</b> {target_formatted}",
            f"┃ {PE['shield']} <b>Снял:</b> {issuer_formatted}",
            f"┃ {PE['tools']} <b>Статус:</b> Ранг аннулирован",
            div_b
        ]
    elif action_type == 'maxban':
        creator_h = extra.get("creator_handle", "@k3rnel8633") if extra else "@k3rnel8633"
        lines = [
            div_t,
            f"┃ {PE['skull']} <b>ВЫСШАЯ МЕРА: МАКСБАН (НАВСЕГДА)</b>",
            div_m,
            f"┃ {PE['user']} <b>Попуск:</b> {target_formatted}",
            f"┃ {PE['shield']} <b>Палач:</b> {issuer_formatted}",
            f"┃ {PE['clock']} <b>Срок:</b> <code>БЕССРОЧНО И БЕЗВОЗВРАТНО</code>",
            f"┃ {PE['crown']} <b>Разработчик AI FOR COPIL:</b> <b>{creator_h}</b>",
            f"┃ {PE['robot']} <b>Бот-помощник:</b> <i>Разработан {creator_h}</i>",
            f"┃ {PE['pencil']} <b>Причина:</b> <i>{clean_reason}</i>",
            div_b
        ]
    else:
        lines = [
            div_t,
            f"┃ {PE['shield']} <b>ДЕЙСТВИЕ: {html.escape(action_type.upper())}</b>",
            div_m,
            f"┃ {PE['user']} <b>Пользователь:</b> {target_formatted}",
            f"┃ {PE['shield']} <b>Модератор:</b> {issuer_formatted}",
            div_b
        ]

    return "\n".join(lines)

def generate_staff_message(bot, chat_id):
    """Generates a stylish hierarchy staff board."""
    chat_data = get_chat_data(chat_id)
    
    # Refresh owner & admins from Telegram if possible
    try:
        admins = bot.get_chat_administrators(chat_id)
        for adm in admins:
            u = adm.user
            uname = (u.first_name or "") + (" " + u.last_name if u.last_name else "")
            register_user_info(chat_id, u)
            if adm.status == "creator":
                chat_data["owner_id"] = u.id
                chat_data["owner_name"] = uname.strip()
                chat_data["owner_username"] = u.username or ""
    except Exception as e:
        logger.debug(f"get_chat_administrators error: {e}")
        
    update_chat_data(chat_id, chat_data)
    
    lines = [f"{PE['crown']} <b>СОСТАВ АДМИНИСТРАЦИИ</b>", ""]
    
    # Owner
    lines.append(f"{PE['crown']} <b>Владелец:</b>")
    if chat_data.get("owner_id"):
        lines.append(f"└ {format_user_mention(chat_data['owner_id'], chat_data.get('owner_name'), chat_data.get('owner_username'))}")
    else:
        lines.append("└ <i>Не назначен (или скрыт)</i>")
    lines.append("")
    
    # Admins
    lines.append(f"{PE['shield']} <b>Администраторы:</b>")
    admins_dict = chat_data.get("admins", {})
    if admins_dict:
        adm_items = list(admins_dict.items())
        for i, (aid, ainfo) in enumerate(adm_items):
            prefix = "└" if i == len(adm_items) - 1 else "├"
            lines.append(f"{prefix} {format_user_mention(int(aid), ainfo.get('name'), ainfo.get('username'))}")
    else:
        lines.append("└ <i>Список пуст</i>")
    lines.append("")
    
    # Moders
    lines.append(f"{PE['swords']} <b>Модерация:</b>")
    moders_dict = chat_data.get("moders", {})
    if moders_dict:
        mod_items = list(moders_dict.items())
        for i, (mid, minfo) in enumerate(mod_items):
            prefix = "└" if i == len(mod_items) - 1 else "├"
            lines.append(f"{prefix} {format_user_mention(int(mid), minfo.get('name'), minfo.get('username'))}")
    else:
        lines.append("└ <i>Список пуст</i>")

    # Custom Staff Roles
    custom_roles = chat_data.get("custom_roles", {})
    if custom_roles:
        for r_key, r_info in custom_roles.items():
            r_title = r_info.get("title", "Персонал")
            r_rights = r_info.get("rights", "moder")
            r_lvl = int(r_info.get("role_lvl", 1))
            rights_badge = {
                "owner": "Права: Создатель",
                "deputy": "Права: Зам / Куратор",
                "admin": "Права: Админ",
                "moder": "Права: Модер",
                "helper": "Права: Хелпер",
                "trainee": "Права: Стажёр",
                "user": "Права: Участник"
            }.get(r_rights, f"Права: {r_rights}")
            
            if r_rights == 'owner':
                icon = PE.get('crown')
            elif r_rights in ['deputy', 'admin']:
                icon = PE.get('shield')
            elif r_rights in ['moder', 'helper', 'trainee']:
                icon = PE.get('swords')
            else:
                icon = PE.get('user')
            lines.append("")
            lines.append(f"{icon} <b>{html.escape(r_title)}:</b> <i>({rights_badge})</i>")
            
            members = r_info.get("members", {})
            if members:
                m_items = list(members.items())
                for i, (mid, minfo) in enumerate(m_items):
                    prefix = "└" if i == len(m_items) - 1 else "├"
                    lines.append(f"{prefix} {format_user_mention(int(mid), minfo.get('name'), minfo.get('username'))}")
            else:
                lines.append("└ <i>Список пуст</i>")
        
    return "\n".join(lines)

# ==========================================
# MODERATION COMMAND GUIDES & SYNTAX HELPERS
# ==========================================

MODERATION_GUIDES = {
    "staff": {
        "title": "УПРАВЛЕНИЕ СТАФФОМ И РОЛЯМИ",
        "desc": "Показывает иерархию администрации чата и позволяет создавать кастомные группы/роли (напр. Хелперы, Кураторы, Пидоры).",
        "perms": f"{PE['crown']} Владелец, {PE['shield']} Админ",
        "syntax": "• Состав: <code>/staff</code>\n• Создать роль: <code>/staff add [права] [название]</code>\n• Редактировать: <code>/staff read [новые_права] [название]</code>\n• Назначить: <code>/staff add @ник [права] [название]</code>\n• Удалить роль: <code>/staff del [название]</code>",
        "units": "Права: созд (3), зам (2), админ (2), модер (1), хелпер (1), стажер (1), юзер (0)",
        "examples": [
            "/staff",
            "/staff add админ Пидоры",
            "/staff add хелпер Хелперы",
            "/staff read хелпер Следящие за чатом",
            "/staff read зам Руководство",
            "/staff add @user Пидоры",
            "/staff del Пидоры"
        ]
    },
    "ban": {
        "title": "БЛОКИРОВКА (БАН)",
        "desc": "Исключает нарушителя из группы и навсегда/временно блокирует повторный вход.",
        "perms": f"{PE['crown']} Владелец (навсегда), {PE['shield']} Админ (до 30 дней), {PE['swords']} Модер (до 10 дней)",
        "syntax": "• Ответом: <code>бан [срок] [причина]</code>\n• По нику: <code>/ban @username [срок] [причина]</code>",
        "units": "10m (мин), 2h (часы), 1d / 7d (дни), навсегда",
        "examples": [
            "бан 30 мин спам (ответом)",
            "/ban @username 1d 18+ контент",
            "/ban @username навсегда рейдер"
        ]
    },
    "mute": {
        "title": "МУТ (РЕЖИМ ЧТЕНИЯ)",
        "desc": "Запрещает нарушителю писать сообщения, отправлять медиа, стикеры и голосовые.",
        "perms": f"{PE['crown']} Владелец (навсегда), {PE['shield']} Админ (до 30 дней), {PE['swords']} Модер (до 10 дней)",
        "syntax": "• Ответом: <code>мут [срок] [причина]</code>\n• По нику: <code>/mute @username [срок] [причина]</code>",
        "units": "10m, 30m, 1h, 12h, 1d, 7d",
        "examples": [
            "мут 15 мин флуд (ответом)",
            "/mute @username 1h оскорбления",
            "/mute @username 1d капс и спам"
        ]
    },
    "kick": {
        "title": "КИК (ИСКЛЮЧЕНИЕ)",
        "desc": "Выгоняет участника из чата. В отличие от бана, участник может вернуться по ссылке.",
        "perms": f"{PE['crown']} Владелец, {PE['shield']} Админ, {PE['swords']} Модератор",
        "syntax": "• Ответом: <code>кик [причина]</code>\n• По нику: <code>/kick @username [причина]</code>",
        "units": "Однократное действие",
        "examples": [
            "кик неадекват (ответом)",
            "/kick @username реклама в лс"
        ]
    },
    "warn": {
        "title": "ПРЕДУПРЕЖДЕНИЕ (ВАРН)",
        "desc": "Выдаёт официальный варн. При достижении 3/3 варнов нарушитель автоматически получает авто-мут на 24 часа.",
        "perms": f"{PE['crown']} Владелец, {PE['shield']} Админ, {PE['swords']} Модератор",
        "syntax": "• Ответом: <code>варн [причина]</code>\n• По нику: <code>/warn @username [причина]</code>",
        "units": "Система 3/3 варнов",
        "examples": [
            "варн флуд (ответом)",
            "/warn @username токсичность и мат"
        ]
    },
    "unban": {
        "title": "РАЗБАН (СНЯТИЕ БЛОКИРОВКИ)",
        "desc": "Снимает бан с пользователя и разрешает ему снова войти в беседу.",
        "perms": f"{PE['crown']} Владелец, {PE['shield']} Админ, {PE['swords']} Модератор",
        "syntax": "• По нику / ID: <code>/unban @username</code> или <code>разбан 123456789</code>",
        "units": "Мгновенно",
        "examples": [
            "/unban @username",
            "разбан 6363403785"
        ]
    },
    "unmute": {
        "title": "РАЗМУТ (СНЯТИЕ МУТА)",
        "desc": "Досрочно возвращает пользователю право писать и отправлять медиа в чат.",
        "perms": f"{PE['crown']} Владелец, {PE['shield']} Админ, {PE['swords']} Модератор",
        "syntax": "• Ответом: <code>размут</code>\n• По нику: <code>/unmute @username</code>",
        "units": "Мгновенно",
        "examples": [
            "размут (ответом)",
            "/unmute @username"
        ]
    },
    "unwarn": {
        "title": "СНЯТИЕ ВАРНА (РАЗВАРН)",
        "desc": "Снимает 1 предупреждение (варн) с пользователя.",
        "perms": f"{PE['crown']} Владелец, {PE['shield']} Админ, {PE['swords']} Модератор",
        "syntax": "• Ответом: <code>разварн</code>\n• По нику: <code>/unwarn @username</code>",
        "units": "-1 варн",
        "examples": [
            "разварн (ответом)",
            "/unwarn @username"
        ]
    },
    "promote": {
        "title": "НАЗНАЧЕНИЕ В ПЕРСОНАЛ",
        "desc": "Назначает участника на должность Модератора или Администратора группы.",
        "perms": f"{PE['crown']} Владелец (на Админа и Модера), {PE['shield']} Админ (только на Модера)",
        "syntax": "• Ответом: <code>!модер</code> или <code>!админ</code>\n• По нику: <code>/promote @username moder</code>",
        "units": "Ранги: moder, admin",
        "examples": [
            "!модер (ответом)",
            "/promote @username moder",
            "/promote @username admin"
        ]
    },
    "demote": {
        "title": "СНЯТИЕ С ДОЛЖНОСТИ",
        "desc": "Снимает модератора или администратора с должности и возвращает статус обычного участника.",
        "perms": f"{PE['crown']} Владелец (любых), {PE['shield']} Админ (только модеров)",
        "syntax": "• Ответом: <code>!снять</code>\n• По нику: <code>/demote @username</code>",
        "units": "Мгновенно",
        "examples": [
            "!снять (ответом)",
            "/demote @username"
        ]
    },
    "clear": {
        "title": "ОЧИСТКА СООБЩЕНИЙ",
        "desc": "Быстро удаляет последние сообщения в группе для очистки от спама.",
        "perms": f"{PE['crown']} Владелец, {PE['shield']} Администратор",
        "syntax": "<code>/clear [число от 1 до 100]</code> или <code>!очистить [число]</code>",
        "units": "От 1 до 100 сообщений",
        "examples": [
            "/clear 10",
            "!очистить 50"
        ]
    },
    "slowmode": {
        "title": "МЕДЛЕННЫЙ РЕЖИМ (SLOWMODE)",
        "desc": "Устанавливает задержку между сообщениями участников для защиты от флуда.",
        "perms": f"{PE['crown']} Владелец, {PE['shield']} Администратор",
        "syntax": "<code>/slowmode [секунды]</code> или <code>!слоумод [сек]</code>",
        "units": "0 (выкл), 10, 30, 60, 300 (5 мин), 900 (15 мин)",
        "examples": [
            "/slowmode 10",
            "/slowmode 0 (отключить)"
        ]
    },
    "rules": {
        "title": "ПРАВИЛА ЧАТА",
        "desc": "Просмотр и настройка официальных правил группы.",
        "perms": f"Просмотр: Все. Установка: {PE['crown']} Владелец, {PE['shield']} Админ",
        "syntax": "• Просмотр: <code>/rules</code> или <code>!правила</code>\n• Задать: <code>/setrules [текст правил]</code>",
        "units": "Текст с поддержкой форматирования",
        "examples": [
            "/rules",
            "/setrules 1. Без спама 2. Уважать участников"
        ]
    }
}

def format_moderation_guide_card(cmd_key):
    """Formats a rich command explanation card with permissions, syntax, time units, and copyable examples."""
    norm_key = str(cmd_key or '').lower().replace('/', '').replace('!', '').replace('.', '').strip()
    synonyms = {
        "бан": "ban", "забанить": "ban", "block": "ban",
        "мут": "mute", "замутить": "mute", "silence": "mute",
        "кик": "kick", "кикнуть": "kick", "пнуть": "kick",
        "варн": "warn", "пред": "warn", "warning": "warn", "предупреждение": "warn",
        "разбан": "unban", "разбанить": "unban",
        "размут": "unmute", "размутить": "unmute",
        "разварн": "unwarn", "снятьварн": "unwarn", "снятьпред": "unwarn",
        "админ": "promote", "модер": "promote", "назначить": "promote", "повысить": "promote", "setadmin": "promote", "setmoder": "promote",
        "снять": "demote", "разжаловать": "demote", "unadmin": "demote", "unmoder": "demote",
        "очистить": "clear", "чистка": "clear", "purge": "clear", "удалить": "clear",
        "слоумод": "slowmode", "задержка": "slowmode", "замедление": "slowmode",
        "правила": "rules", "сетправила": "rules", "setrules": "rules", "сетрулс": "rules",
        "автомодер": "automod", "автомод": "automod", "automoder": "automod", "automod": "automod"
    }
    actual_key = synonyms.get(norm_key, norm_key)
    info = MODERATION_GUIDES.get(actual_key)
    if not info:
        return None
    
    lines = [
        f"{PE.get('book', '📖')} <b>Инструкция: {html.escape(info['title'])}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"{PE.get('pencil', '📝')} <b>Назначение:</b> {html.escape(info['desc'])}",
        f"{PE.get('shield', '🛡')} <b>Кто может:</b> {info['perms']}",
        "",
        f"{PE.get('gear', '⚙️')} <b>Синтаксис:</b>",
    ]
    for s_line in info['syntax'].splitlines():
        lines.append(f"• {s_line}")
    lines.extend([
        "",
        f"{PE.get('clock', '⏳')} <b>Форматы времени:</b> <code>{html.escape(info['units'])}</code>",
        "",
        f"{PE.get('bulb', '💡')} <b>Примеры для использования:</b>"
    ])
    for ex in info['examples']:
        lines.append(f"• <code>{html.escape(ex)}</code>")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    return chr(10).join(lines)

def get_full_moderation_guide():
    """Returns full comprehensive cheat sheet for moderators and admins."""
    div_t = "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓"
    div_m = "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫"
    div_b = "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
    
    lines = [
        div_t,
        f"┃ {PE['shield']} <b>ШПАРГАЛКА МОДЕРАТОРА (MOD HELP)</b>",
        div_m,
        f"┃ {PE['swords']} <b>НАКАЗАНИЯ И ОГРАНИЧЕНИЯ:</b>",
        "┃ • <code>/ban [срок] [причина]</code> — Бан в группе",
        "┃ • <code>/mute [срок] [причина]</code> — Мут (режим чтения)",
        "┃ • <code>/kick [причина]</code> — Пнуть из чата (без бана)",
        "┃ • <code>/warn [причина]</code> — Варн (3/3 = авто-мут на 24ч)",
        "┃ • <code>/unban [@ник/ID]</code> — Разбанить участника",
        "┃ • <code>/unmute [@ник/ID]</code> — Досрочно снять мут",
        "┃ • <code>/unwarn [@ник/ID]</code> — Снять 1 варн",
        "┃ ",
        f"┃ {PE['robot']} <b>АВТОМОДЕРАЦИЯ И ЗАЩИТА:</b>",
        "┃ • <code>/automoder</code> (<code>/automod</code>) — Настройка фильтров мата, 18+, ссылок",
        "┃ ",
        f"┃ {PE['crown']} <b>УПРАВЛЕНИЕ И ПЕРСОНАЛ:</b>",
        "┃ • <code>/promote [@ник] [admin/moder]</code> — Назначить ранг",
        "┃ • <code>/demote [@ник]</code> — Снять с должности",
        "┃ • <code>/staff</code> — Показать состав администрации",
        "┃ • <code>/clear [1-100]</code> — Удалить N сообщений",
        "┃ • <code>/slowmode [сек]</code> — Задержка отправки",
        "┃ • <code>/setrules [текст]</code> — Установить правила",
        "┃ • <code>/rules</code> — Прочитать правила чата",
        "┃ ",
        f"┃ {PE['clock']} <b>Форматы времени:</b>",
        "┃ <code>10m</code> = 10 минут | <code>2h</code> = 2 часа",
        "┃ <code>1d</code> = 1 день | <code>7d</code> = 7 дней | <code>навсегда</code>",
        "┃ ",
        f"┃ {PE['bulb']} <b>Любую команду можно писать ответом:</b>",
        "┃ Пример: ответь на спам словом <code>бан 1д спам</code>!",
        div_b
    ]
    return "\n".join(lines)


# ==========================================
# AUTOMODERATION ENGINE (/automoder, /automod)
# ==========================================

import collections
import requests

# Regex character normalizer to combat l33t speak / latin substitutes in Russian profanities
_HOMOGLYPHS = {
    'a': 'а', 'b': 'в', 'c': 'с', 'e': 'е', 'k': 'к', 'm': 'м', 'h': 'н',
    'o': 'о', 'p': 'р', 't': 'т', 'x': 'х', 'y': 'у', 'u': 'у',
    '0': 'о', '1': 'и', '3': 'з', '4': 'ч', '@': 'а', '$': 'с', '!': 'и',
    '6': 'б', 'w': 'в', 'v': 'в', 'z': 'з', 'd': 'д', 'n': 'н', 'r': 'р',
    'g': 'г', 'i': 'и', 'j': 'й', 'l': 'л', 's': 'с', 'q': 'к'
}

def normalize_text_for_filter(text):
    """Normalizes text by replacing homoglyphs and punctuation separators."""
    if not text:
        return ""
    t = str(text).lower()
    for lat, cyr in _HOMOGLYPHS.items():
        t = t.replace(lat, cyr)
    return t

def remove_spaces_and_punct(text):
    """Strips all spaces, punctuation and non-alphanumeric chars to catch spaced-out bypasses."""
    t = normalize_text_for_filter(text)
    return re.sub(r'[^а-яёa-z0-9]', '', t)

# Innocent words that contain 'еб' / 'ху' / 'пизд' / 'стрим' substrings but are completely non-profane
_INNOCENT_WORDS_RE = re.compile(
    r'\b\w*(?:'
    r'стрим|stream|стример|стримить|стримы|стримерша|стриминг|'
    r'хлеб|реб[её]н|ребят|стебел|стебл|греб|грест|тереб|колеб|ястреб|погреб|'
    r'страхован|страховк|штрих|трихопол|бархат|гребеш|педагог|рубл|рупи|'
    r'педиатри|эпилеп|скипидар|команд|скипетр|потреб|употреб|учеб|серебр|'
    r'барсук|суккулент|сукно|пылесос|насос|целебн|врачебн|судебн'
    r')\w*\b',
    re.IGNORECASE
)

# Profanity roots regex (precision tuned to prevent false positives on words like серебро, учеба, стрим)
_MAT_CORE = (
    r'(?:'
    r'пизд[а-яa-z]*|п[её]зд[а-яa-z]*|'
    r'(?:\b|(?<=[^а-яёa-z0-9]))ху[йеяиюеё][а-яa-z]*|'
    r'(?:\b|(?<=[^а-яёa-z0-9]))(?:на|по|до|ни|о|а|за|с|от)ху[йеяиюеё][а-яa-z]*|'
    r'(?:\b|(?<=[^а-яёa-z0-9]))[её]б[а-яa-z]+|'
    r'(?:\b|(?<=[^а-яёa-z0-9]))(?:въ|вь|вы|до|за|на|недо|объ|обь|отъ|от|осто|пере|по|подъ|под|при|про|разъ|раз|съ|сь|у)[её]б[а-яa-z]*|'
    r'долбо[её]б[а-яa-z]*|'
    r'у[её]б(?:ок|ки|к[а-яa-z]*|ищ[а-яa-z]*)|'
    r'ебл[а-яa-z]*|ебан[а-яa-z]*|ёбан[а-яa-z]*|ебать|ебуч[а-яa-z]*|ёбуч[а-яa-z]*|ебыр[а-яa-z]*|ёбыр[а-яa-z]*|'
    r'бля[дт][а-яa-z]*|'
    r'(?:\b|(?<=[^а-яёa-z0-9]))сук[аиеоу]\b|'
    r'(?:\b|(?<=[^а-яёa-z0-9]))сучк[а-яa-z]*|'
    r'(?:\b|(?<=[^а-яёa-z0-9]))(?:мудак|мудил|мудозвон|мудач)[а-яa-z]*|'
    r'гандон[а-яa-z]*|гондон[а-яa-z]*|залуп[а-яa-z]*|'
    r'(?:\b|(?<=[^а-яёa-z0-9]))пид[ао]р[а-яa-z]*|'
    r'(?:\b|(?<=[^а-яёa-z0-9]))педик[а-яa-z]*|'
    r'пидорас[а-яa-z]*|пидарас[а-яa-z]*|'
    r'(?:\b|(?<=[^а-яёa-z0-9]))чм[оеау](?:\b|(?=[^а-яёa-z0-9]))|'
    r'(?:\b|(?<=[^а-яёa-z0-9]))чмошн[а-яa-z]*|'
    r'(?:\b|(?<=[^а-яёa-z0-9]))(?:по|пере|вы|раз)?трах[а-яa-z]+|'
    r'шлюх[а-яa-z]*|(?:\b|(?<=[^а-яёa-z0-9]))(?:по)?дроч[а-яa-z]*|шалав[а-яa-z]*|'
    r'(?:\b|(?<=[^а-яёa-z0-9]))говн[а-яa-z]*|'
    r'(?:\b|(?<=[^а-яёa-z0-9]))жоп[а-яa-z]*|'
    r'(?:\b|(?<=[^а-яёa-z0-9]))соси(?:\b|(?=[^а-яёa-z0-9]))|'
    r'отсос[а-яa-z]*'
    r')'
)
_MAT_REGEX = re.compile(r'(?iu)' + _MAT_CORE, re.IGNORECASE)

# 18+ / Pornographic keywords
_PORN_18_KEYWORDS = [
    "порно", "porn", "hentai", "хентай", "эротика", "childporn", "слив 18", "сливы 18",
    "18+ слив", "нюдсы", "дрочить", "дрочка", "мастурб", "сиськи", "член", "сперма",
    "камшот", "cumshot", "blowjob", "минет", "отсос", "анал", "секс видео", "секс фото",
    "шлюха", "проститутка", "вебкам", "webcam", "onlyfans", "онлифанс", "порнуха", "порнушка",
    "xvideos", "pornhub", "xhamster", "brazzers", "redtube", "xnxx", "rule34", "nhentai", "hanime"
]

# External & Invite links regex
_LINKS_REGEX = re.compile(
    r'(?i)(https?://\S+|t\.me/(?!\b(?:pomoshotru_bot|k3rnel8633)\b)\S+|telegram\.me/\S+|discord\.gg/\S+|vk\.com/\S+|tg://join\S+)',
    re.IGNORECASE
)

# Rolling buffer of recent messages per user in chat to catch insults split across 2-3 messages
_USER_RECENT_MSGS = {}  # {scope_key: {user_id: deque(maxlen=4)}}

def record_user_message(chat_id, user_id, msg_id, text, thread_id=None):
    """Records user message for multi-message evasion tracking."""
    if not chat_id or not user_id or not text:
        return
    now = time.time()
    scope_key = f"{chat_id}_{thread_id}" if thread_id is not None else chat_id
    chat_dict = _USER_RECENT_MSGS.setdefault(scope_key, {})
    user_deque = chat_dict.setdefault(user_id, collections.deque(maxlen=4))
    user_deque.append({"msg_id": msg_id, "text": text, "time": now})

def get_recent_user_sequence(chat_id, user_id, max_age=25.0, thread_id=None):
    """Retrieves recent messages from a user within max_age seconds."""
    scope_key = f"{chat_id}_{thread_id}" if thread_id is not None else chat_id
    chat_dict = _USER_RECENT_MSGS.get(scope_key, {})
    user_deque = chat_dict.get(user_id)
    if not user_deque:
        return []
    now = time.time()
    return [m for m in user_deque if (now - m["time"]) <= max_age]

def clear_user_recent_messages(chat_id, user_id, thread_id=None):
    scope_key = f"{chat_id}_{thread_id}" if thread_id is not None else chat_id
    chat_dict = _USER_RECENT_MSGS.get(scope_key, {})
    if user_id in chat_dict:
        chat_dict[user_id].clear()

def check_ai_violation(text, history_list=None):
    """
    Calls Gemini Flash Lite to detect obfuscated Russian profanities, insults, family attacks,
    or multi-message evasion attempts (e.g. 'еб' -> 'ал' -> 'мать' -> 'зени').
    Returns (is_violation, reason)
    """
    if not text or len(text.strip()) < 1:
        return False, None
    try:
        import config
        api_key = config.GEMINI_API_KEY
        if not api_key:
            return False, None

        history_str = "\n".join([f"- \"{h}\"" for h in history_list]) if history_list else "(нет)"

        prompt = (
            "Ты строгий, но справедливый ИИ-автомодератор русскоязычного чата Telegram.\n"
            "Твоя задача — пресекать мат, тяжелые оскорбления, травлю, наезды на создателей/админов (зени, k3rnel), "
            "наезды на родителей ('мать', 'мамка', 'батя') и ЛЮБЫЕ попытки обхода фильтра, когда пользователь разбивает "
            "маты или оскорбления на несколько коротких сообщений подряд (например: 'еб' -> 'ал' -> 'мать' -> 'зени').\n\n"
            "ВАЖНО:\n"
            "- Обычные разговорные, бытовые или игровые слова (например: 'стрим', 'стримить', 'игра', 'привет', 'ок', 'да', 'нет', 'хлеб', 'учеба', 'барсук', 'ссылка', 'бот', 'комп') — это АБСОЛЮТНО ЧИСТЫЙ текст! Запрещено выдумывать нарушения!\n"
            "- Если нет явного мата, оскорблений или травли — ВСЕГДА отвечай CLEAN.\n\n"f"Предыдущие сообщения этого пользователя за последние секунды:\n{history_str}\n\n"
            f"Текущее новое сообщение:\n\"{text}\"\n\n"
            "Правила ответа:\n"
            "Если текущее сообщение (само по себе или в связке с предыдущими) образует мат, оскорбление или обход фильтра, ответь СТРОГО:\n"
            "VIOLATION: <краткое описание, например: ебал мать зени>\n\n"
            "Если текст полностью безобиден, чист и не образует мата/оскорблений, ответь СТРОГО:\n"
            "CLEAN"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={api_key}"
        resp = requests.post(
            url,
            json={"contents": [{"role": "user", "parts": [{"text": prompt}]}]},
            timeout=2.2
        )
        if resp.status_code == 200:
            res_txt = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            if res_txt.startswith("VIOLATION:"):
                reason = res_txt.replace("VIOLATION:", "").strip() or "Завуалированный мат / оскорбление"
                return True, reason
    except Exception as e:
        logger.debug(f"AI automod check error: {e}")
    return False, None

def check_automod_violation(text="", media_type="text", media_info="", settings=None, chat_id=None, user_id=None, msg_id=None, thread_id=None):
    """
    Checks if a message violates active chat automod rules.
    Returns (violation_type, violation_description, extra_msg_ids_to_delete).
    """
    if not settings:
        return None, None, []

    full_text = f"{text or ''} {media_info or ''}".strip()
    norm_text = normalize_text_for_filter(full_text)
    nospace_text = remove_spaces_and_punct(full_text)

    # 1. 18+ / NSFW Media Check (Stickers, Videos, Photos, Animations)
    if settings.get("anti_nsfw_media", 1):
        if media_type in ["sticker", "animation", "video", "photo", "document"]:
            m_info_low = str(media_info or "").lower()
            nsfw_media_tags = [
                "porn", "hentai", "ero", "nsfw", "18plus", "xxx", "nude", "boobs", "milf",
                "hentaigirls", "lewd", "ecchi", "r34", "rule34", "sexy", "adult", "erotic",
                "порно", "хентай", "нюдсы", "эротика"
            ]
            if any(tag in m_info_low for tag in nsfw_media_tags):
                return "nsfw_media", "18+ / NSFW Стикер или медиафайл", []

    # 2. 18+ Text / Pornography Check
    if settings.get("anti_18plus", 1):
        for kw in _PORN_18_KEYWORDS:
            kw_clean = remove_spaces_and_punct(kw)
            if kw in norm_text or (kw_clean and kw_clean in nospace_text):
                return "18plus", "18+ / Порнографический контент", []

    # 3. Profanity / Anti-Mat Check (Whole words and space-stripped text)
    if settings.get("anti_mat", 1):
        # A. Check isolated words
        words = re.findall(r'\b\w+\b', norm_text)
        has_mat = False
        for w in words:
            if _INNOCENT_WORDS_RE.fullmatch(w):
                continue
            if _MAT_REGEX.search(w):
                has_mat = True
                break

        # B. Check condensed text without spaces (e.g. 'е б а л', 'е.б.а.л', 'еб ал')
        if not has_mat and nospace_text and len(nospace_text) >= 3:
            if not _INNOCENT_WORDS_RE.fullmatch(nospace_text):
                if _MAT_REGEX.search(nospace_text):
                    has_mat = True

        if has_mat:
            return "mat", "Ненормативная лексика / Мат", []

    # 4. Links / Advertising Check
    if settings.get("anti_links", 0):
        if _LINKS_REGEX.search(full_text):
            return "links", "Несанкционированная ссылка / Реклама", []

    # 5. Multi-message concatenation check & AI check on EVERY message
    extra_ids = []
    recent_texts = []
    if chat_id and user_id and text:
        recent_seq = get_recent_user_sequence(chat_id, user_id, max_age=30.0, thread_id=thread_id)
        if recent_seq:
            extra_ids = [m["msg_id"] for m in recent_seq]
            recent_texts = [m["text"] for m in recent_seq]
            chained_text = " ".join(recent_texts + [text])
            chained_nospace = remove_spaces_and_punct(chained_text)

            # Fast regex on chained multi-message sequence
            if settings.get("anti_mat", 1) and _MAT_REGEX.search(chained_nospace):
                return "mat", "Ненормативная лексика / Мат (разделено по сообщениям)", extra_ids

            if settings.get("anti_18plus", 1):
                for kw in _PORN_18_KEYWORDS:
                    kw_clean = remove_spaces_and_punct(kw)
                    if kw_clean and kw_clean in chained_nospace:
                        return "18plus", "18+ контент (разделено по сообщениям)", extra_ids

    # 6. AI Inspection for EVERY message in automod chat (catches evasions, multi-message splits, hidden toxicity)
    if settings.get("anti_ai", 1) and text:
        # Skip AI inspection if message consists purely of innocent whitelist words (e.g. 'стрим')
        if not _INNOCENT_WORDS_RE.fullmatch(nospace_text):
            is_v, reason = check_ai_violation(text, history_list=recent_texts)
            if is_v:
                return "ai_toxic", f"ИИ: {reason}", extra_ids

    return None, None, []

def parse_duration_to_seconds(dur_str):
    """Converts duration string to seconds."""
    dur = str(dur_str or '30m').strip().lower()
    if dur in ["forever", "0", "навсегда", "perm", "permanent", "вечно"]:
        return 0
    m = re.match(r'^(\d+)\s*([mhdw])$', dur)
    if m:
        val = int(m.group(1))
        unit = m.group(2)
        if unit == 'm': return val * 60
        if unit == 'h': return val * 3600
        if unit == 'd': return val * 86400
        if unit == 'w': return val * 7 * 86400
    presets = {
        "15m": 15 * 60,
        "30m": 30 * 60,
        "1h": 3600,
        "2h": 7200,
        "12h": 12 * 3600,
        "24h": 86400,
        "1d": 86400,
        "3d": 3 * 86400,
        "7d": 7 * 86400,
        "30d": 30 * 86400
    }
    return presets.get(dur, 1800)

def format_duration_title(dur_str):
    """Returns Russian display label for punishment duration."""
    dur = str(dur_str or '30m').strip().lower()
    labels = {
        "15m": "15 минут",
        "30m": "30 минут",
        "1h": "1 час",
        "2h": "2 часа",
        "12h": "12 часов",
        "24h": "24 часа (1 день)",
        "1d": "1 день",
        "3d": "3 дня",
        "7d": "7 дней (1 неделя)",
        "30d": "30 дней (1 месяц)",
        "forever": "Навсегда",
        "0": "Навсегда"
    }
    return labels.get(dur, dur)

def get_automod_action_title(action_code):
    actions = {
        "warn": "⚠️ Варны + Наказание при превышении",
        "mute": "🔇 Сразу Мут",
        "ban": "⛔️ Сразу Бан",
        "kick": "👢 Сразу Кик",
        "delete": "🗑 Только удаление"
    }
    return actions.get(str(action_code or 'warn').lower(), "⚠️ Варны + Наказание при превышении")

def format_automod_menu(chat_id, settings, thread_id=None, is_topic_enabled=True):
    """Formats the visual dashboard card and interactive inline buttons for /automoder with forum topic support."""
    mat_s = "🟢 ВКЛ" if settings.get("anti_mat", 1) else "🔴 ВЫКЛ"
    p18_s = "🟢 ВКЛ" if settings.get("anti_18plus", 1) else "🔴 ВЫКЛ"
    med_s = "🟢 ВКЛ" if settings.get("anti_nsfw_media", 1) else "🔴 ВЫКЛ"
    lnk_s = "🟢 ВКЛ" if settings.get("anti_links", 0) else "🔴 ВЫКЛ"
    ai_s = "🟢 ВКЛ" if settings.get("anti_ai", 1) else "🔴 ВЫКЛ"
    ch_s = "🟢 БЛОК" if settings.get("anti_channels", 0) else "⚪️ РАЗРЕШЕНЫ"
    anon_s = "🟢 БЛОК" if settings.get("anti_anonymous", 0) else "⚪️ РАЗРЕШЕНЫ"
    adm_s = "🛡 ИММУНИТЕТ" if settings.get("exempt_admins", 0) else "⚡️ БЕЗ ИММУНИТЕТА (для тестов)"

    act = str(settings.get("action", "warn")).lower()
    warn_lim = settings.get("warn_limit", 3)
    warn_pun = str(settings.get("warn_punishment", "mute")).lower()
    dur = str(settings.get("punishment_duration", "30m")).lower()
    dur_lbl = format_duration_title(dur)

    pun_name = "Бан" if warn_pun == "ban" else ("Кик" if warn_pun == "kick" else "Мут")
    if act == "warn":
        scheme_desc = f"Варны ({warn_lim}) ➡️ {pun_name} на {dur_lbl}"
    elif act == "mute":
        scheme_desc = f"Сразу Мут на {dur_lbl}"
    elif act == "ban":
        scheme_desc = f"Сразу Бан на {dur_lbl}"
    elif act == "kick":
        scheme_desc = "Сразу Кик из группы"
    else:
        scheme_desc = "Только удаление нарушений"

    div_t = "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓"
    div_m = "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫"
    div_b = "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"

    topic_info_line = ""
    cb_suffix = f":{thread_id}" if thread_id is not None else ""
    if thread_id is not None:
        top_st = "🟢 ВКЛ" if is_topic_enabled else "🔴 ВЫКЛ (Свободная зона)"
        topic_info_line = f"┃ 📍 <b>ТЕКУЩИЙ ТОПИК:</b> <code>#{thread_id}</code> [{top_st}]\n"

    text = (
        f"{div_t}\n"
        f"┃ {PE['shield']} <b>ПАНЕЛЬ АВТОМОДЕРАЦИИ ЧАТА</b> ┃\n"
        f"{div_m}\n"
        f"{topic_info_line}"
        f"┃ ⚡️ <i>Защита чата от мата, 18+, ссылок и обходов через ИИ.</i>\n"
        f"┃ ⚙️ <i>Нажмите кнопки ниже для мгновенной настройки правил:</i>\n"
        "┃ \n"
        f"┃ {pe('swear')} <b>Анти-Мат:</b> {mat_s}\n"
        f"┃ {pe('nsfw')} <b>18+ Текст:</b> {p18_s}\n"
        f"┃ {pe('nsfw')} <b>18+ Медиа & Стикеры:</b> {med_s}\n"
        f"┃ {pe('link')} <b>Анти-Ссылки:</b> {lnk_s}\n"
        f"┃ {pe('brain')} <b>ИИ-Детектор (Обходы & Скрытые оски):</b> {ai_s}\n"
        f"┃ 📢 <b>Анти-Каналы:</b> {ch_s}\n"
        f"┃ {pe('ninja')} <b>Анти-Анонимность:</b> {anon_s}\n"
        f"┃ {pe('user')} <b>Админы в автомоде:</b> <code>{adm_s}</code>\n"
        f"{div_m}\n"
        f"┃ {pe('scale')} <b>СХЕМА НАКАЗАНИЯ:</b>\n"
        f"┃ ➡️ <code>{html.escape(scheme_desc)}</code>\n"
        f"{div_b}"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton(f"Анти-Мат: [{mat_s}]", callback_data=f"toggle:automod:anti_mat{cb_suffix}", icon_custom_emoji_id=pe_id('swear')),
        types.InlineKeyboardButton(f"ИИ-Анализ: [{ai_s}]", callback_data=f"toggle:automod:anti_ai{cb_suffix}", icon_custom_emoji_id=pe_id('brain'))
    )
    markup.row(
        types.InlineKeyboardButton(f"18+ Текст: [{p18_s}]", callback_data=f"toggle:automod:anti_18plus{cb_suffix}", icon_custom_emoji_id=pe_id('nsfw')),
        types.InlineKeyboardButton(f"18+ Медиа: [{med_s}]", callback_data=f"toggle:automod:anti_nsfw_media{cb_suffix}", icon_custom_emoji_id=pe_id('nsfw'))
    )
    markup.row(
        types.InlineKeyboardButton(f"Ссылки: [{lnk_s}]", callback_data=f"toggle:automod:anti_links{cb_suffix}", icon_custom_emoji_id=pe_id('link')),
        types.InlineKeyboardButton(f"Режим: {act.upper()}", callback_data=f"toggle:automod:action{cb_suffix}", icon_custom_emoji_id=pe_id('gear'))
    )
    markup.row(
        types.InlineKeyboardButton(f"Каналы: [{ch_s}]", callback_data=f"toggle:automod:anti_channels{cb_suffix}", icon_custom_emoji_id=pe_id('movie')),
        types.InlineKeyboardButton(f"Аноним: [{anon_s}]", callback_data=f"toggle:automod:anti_anonymous{cb_suffix}", icon_custom_emoji_id=pe_id('ninja'))
    )

    if act == "warn":
        markup.row(
            types.InlineKeyboardButton(f"Порог: {warn_lim} варна", callback_data=f"toggle:automod:warn_limit{cb_suffix}", icon_custom_emoji_id=pe_id('warning')),
            types.InlineKeyboardButton(f"Итог: {pun_name}", callback_data=f"toggle:automod:warn_punishment{cb_suffix}", icon_custom_emoji_id=pe_id('hammer'))
        )
        markup.row(
            types.InlineKeyboardButton(f"Срок: {dur_lbl}", callback_data=f"toggle:automod:punishment_duration{cb_suffix}", icon_custom_emoji_id=pe_id('clock'))
        )
    elif act in ["mute", "ban"]:
        markup.row(
            types.InlineKeyboardButton(f"Срок: {dur_lbl}", callback_data=f"toggle:automod:punishment_duration{cb_suffix}", icon_custom_emoji_id=pe_id('clock'))
        )

    adm_btn_text = "Иммунитет админов: ВКЛ" if settings.get("exempt_admins", 0) else "Проверять и админов (Тест)"
    markup.row(
        types.InlineKeyboardButton(adm_btn_text, callback_data=f"toggle:automod:exempt_admins{cb_suffix}", icon_custom_emoji_id=pe_id('shield'))
    )
    if thread_id is not None:
        top_btn_title = f"Автомод в этой теме: [{'🟢 ВКЛ' if is_topic_enabled else '🔴 ВЫКЛ'}]"
        markup.row(
            types.InlineKeyboardButton(top_btn_title, callback_data=f"toggle:topic_automod:{thread_id}", icon_custom_emoji_id=pe_id('pin'))
        )

    markup.row(
        types.InlineKeyboardButton("Закрыть панель", callback_data="close_automod", icon_custom_emoji_id=pe_id('cross'))
    )
    return text, markup
