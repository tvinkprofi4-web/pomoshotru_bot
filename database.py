import sqlite3
import os
import time
import datetime
import threading
import logging
import json

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chats.db")
MODERATION_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "moderation_data.json")
BACKUP_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chats_persistent_backup.json")
_db_lock = threading.Lock()
_last_backup_time = 0
_backup_lock = threading.Lock()

def save_persistent_backup(force=False):
    """
    Dumps database tables to chats_persistent_backup.json so all messages, users,
    settings, admins, and modes survive container restarts and deployments.
    """
    global _last_backup_time
    now_ts = time.time()
    if not force and (now_ts - _last_backup_time < 4.0):
        return
    _last_backup_time = now_ts

    with _backup_lock:
        try:
            with _db_lock:
                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute('SELECT * FROM users')
                users = [dict(row) for row in cursor.fetchall()]

                cursor.execute('SELECT * FROM chats')
                chats = [dict(row) for row in cursor.fetchall()]

                cursor.execute('SELECT * FROM messages ORDER BY id DESC LIMIT 10000')
                messages = [dict(row) for row in cursor.fetchall()]
                messages.reverse()

                cursor.execute('SELECT * FROM user_settings')
                user_settings = [dict(row) for row in cursor.fetchall()]

                cursor.execute('SELECT * FROM bot_admins')
                bot_admins = [dict(row) for row in cursor.fetchall()]

                cursor.execute('SELECT * FROM app_settings')
                app_settings = [dict(row) for row in cursor.fetchall()]

                cursor.execute('SELECT * FROM business_connections')
                business_connections = [dict(row) for row in cursor.fetchall()]

                try:
                    cursor.execute('SELECT * FROM business_chats')
                    business_chats = [dict(row) for row in cursor.fetchall()]
                except Exception:
                    business_chats = []

                cursor.execute('SELECT * FROM user_economy')
                user_economy = [dict(row) for row in cursor.fetchall()]

                cursor.execute('SELECT * FROM user_subscriptions')
                user_subscriptions = [dict(row) for row in cursor.fetchall()]

                cursor.execute('SELECT * FROM chat_sniffer_settings')
                chat_sniffer_settings = [dict(row) for row in cursor.fetchall()]

                cursor.execute('SELECT * FROM sniffer_messages ORDER BY created_at DESC LIMIT 2000')
                sniffer_messages = [dict(row) for row in cursor.fetchall()]

                try:
                    cursor.execute('SELECT * FROM blocked_users')
                    blocked_users = [dict(row) for row in cursor.fetchall()]
                except Exception:
                    blocked_users = []

                # Secretary per-chat modes & enabled flags (survive deploys so .a_troll/.bot settings persist)
                try:
                    cursor.execute('SELECT * FROM secretary_chat_modes')
                    secretary_chat_modes = [dict(row) for row in cursor.fetchall()]
                except Exception:
                    secretary_chat_modes = []
                try:
                    cursor.execute('SELECT * FROM secretary_chat_status')
                    secretary_chat_status = [dict(row) for row in cursor.fetchall()]
                except Exception:
                    secretary_chat_status = []

                # Automod filter settings (anti-mat, anti-links, warn limits, actions)
                try:
                    cursor.execute('SELECT * FROM chat_automod')
                    chat_automod = [dict(row) for row in cursor.fetchall()]
                except Exception:
                    chat_automod = []

                # Muted business chats (.mute)
                try:
                    cursor.execute('SELECT * FROM secretary_chat_mutes')
                    secretary_chat_mutes = [dict(row) for row in cursor.fetchall()]
                except Exception:
                    secretary_chat_mutes = []

                # Forum supergroup topics modes & automod
                try:
                    cursor.execute('SELECT * FROM chat_topics')
                    chat_topics = [dict(row) for row in cursor.fetchall()]
                except Exception:
                    chat_topics = []

                # Chat targets (.target / .a_troll)
                try:
                    cursor.execute('SELECT * FROM chat_targets')
                    chat_targets = [dict(row) for row in cursor.fetchall()]
                except Exception:
                    chat_targets = []

                # Always online user state
                try:
                    cursor.execute('SELECT * FROM user_always_online')
                    user_always_online = [dict(row) for row in cursor.fetchall()]
                except Exception:
                    user_always_online = []

                # Chat moderation configs (SQLite mirrored)
                try:
                    cursor.execute('SELECT * FROM chat_moderation_config')
                    chat_moderation_config = [dict(row) for row in cursor.fetchall()]
                except Exception:
                    chat_moderation_config = []

                # Moderation data backup (rules, warns, custom roles, admins, automod)
                moderation_payload = {}
                try:
                    mod_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "moderation_data.json")
                    if os.path.exists(mod_json_path):
                        with open(mod_json_path, "r", encoding="utf-8") as mf:
                            moderation_payload = json.load(mf)
                except Exception as _me:
                    logger.debug(f"Moderation dump notice: {_me}")

                if not isinstance(moderation_payload, dict):
                    moderation_payload = {}
                if "chats" not in moderation_payload or not isinstance(moderation_payload["chats"], dict):
                    moderation_payload["chats"] = {}

                # Merge any missing chats from SQLite chat_moderation_config
                for cmc in chat_moderation_config:
                    cid_key = str(cmc.get("chat_id"))
                    if cid_key and cid_key not in moderation_payload["chats"]:
                        try:
                            moderation_payload["chats"][cid_key] = json.loads(cmc.get("config_json", "{}"))
                        except Exception:
                            pass

                conn.close()

            payload = {
                "_version": 1,
                "_saved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "users": users,
                "chats": chats,
                "messages": messages,
                "user_settings": user_settings,
                "bot_admins": bot_admins,
                "app_settings": app_settings,
                "business_connections": business_connections,
                "business_chats": business_chats,
                "user_economy": user_economy,
                "user_subscriptions": user_subscriptions,
                "chat_sniffer_settings": chat_sniffer_settings,
                "sniffer_messages": sniffer_messages,
                "blocked_users": blocked_users,
                "secretary_chat_modes": secretary_chat_modes,
                "secretary_chat_status": secretary_chat_status,
                "chat_automod": chat_automod,
                "secretary_chat_mutes": secretary_chat_mutes,
                "chat_topics": chat_topics,
                "chat_targets": chat_targets,
                "user_always_online": user_always_online,
                "chat_moderation_config": chat_moderation_config,
                "moderation_data": moderation_payload
            }

            temp_path = BACKUP_JSON_PATH + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, BACKUP_JSON_PATH)
        except Exception as e:
            logger.warning(f"Error saving persistent backup: {e}")

def restore_persistent_backup():
    """Restores database tables from chats_persistent_backup.json upon initialization."""
    if not os.path.exists(BACKUP_JSON_PATH):
        return
    try:
        with open(BACKUP_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        restore_backup_payload(data)
    except Exception as e:
        logger.warning(f"Error restoring persistent backup: {e}")

def restore_backup_payload(data):
    """Restores database tables from an in-memory backup payload dict (used by db_sync remote restore)."""
    try:
        if not isinstance(data, dict):
            return

        with _db_lock:
            conn = get_connection()
            cursor = conn.cursor()

            # Users
            for u in data.get("users", []):
                try:
                    cursor.execute('''
                        INSERT INTO users (user_id, username, first_name, last_name, is_creator, first_seen, last_seen, total_messages)
                        VALUES (:user_id, :username, :first_name, :last_name, :is_creator, :first_seen, :last_seen, :total_messages)
                        ON CONFLICT(user_id) DO UPDATE SET
                            username = COALESCE(NULLIF(excluded.username, ''), users.username),
                            first_name = COALESCE(NULLIF(excluded.first_name, ''), users.first_name),
                            last_name = COALESCE(NULLIF(excluded.last_name, ''), users.last_name),
                            is_creator = MAX(users.is_creator, excluded.is_creator),
                            last_seen = excluded.last_seen,
                            total_messages = MAX(users.total_messages, excluded.total_messages)
                    ''', u)
                except Exception:
                    pass

            # Chats
            for c in data.get("chats", []):
                try:
                    cursor.execute('''
                        INSERT INTO chats (chat_id, chat_title, chat_type, created_at, last_activity, message_count)
                        VALUES (:chat_id, :chat_title, :chat_type, :created_at, :last_activity, :message_count)
                        ON CONFLICT(chat_id) DO UPDATE SET
                            chat_title = CASE WHEN excluded.chat_title != '' AND chats.chat_title = '' THEN excluded.chat_title ELSE chats.chat_title END,
                            message_count = MAX(chats.message_count, excluded.message_count)
                    ''', c)
                except Exception:
                    pass

            # Messages
            for m in data.get("messages", []):
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO messages (id, chat_id, user_id, sender_type, sender_name, text, media_type, media_info, timestamp, is_reply_to)
                        VALUES (:id, :chat_id, :user_id, :sender_type, :sender_name, :text, :media_type, :media_info, :timestamp, :is_reply_to)
                    ''', m)
                except Exception:
                    pass

            # User Settings
            for s in data.get("user_settings", []):
                try:
                    cursor.execute('''
                        INSERT INTO user_settings (user_id, mode, voice_style)
                        VALUES (:user_id, :mode, :voice_style)
                        ON CONFLICT(user_id) DO UPDATE SET
                            mode = excluded.mode,
                            voice_style = excluded.voice_style
                    ''', s)
                except Exception:
                    pass

            # Bot Admins
            for ba in data.get("bot_admins", []):
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO bot_admins (user_id, username, first_name, granted_by, granted_at)
                        VALUES (:user_id, :username, :first_name, :granted_by, :granted_at)
                    ''', ba)
                except Exception:
                    pass

            # App Settings
            for asp in data.get("app_settings", []):
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO app_settings (key, value, updated_at)
                        VALUES (:key, :value, :updated_at)
                    ''', asp)
                except Exception:
                    pass

            # User Economy
            for ue in data.get("user_economy", []):
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO user_economy (user_id, reputation, coins, last_daily)
                        VALUES (:user_id, :reputation, :coins, :last_daily)
                    ''', ue)
                except Exception:
                    pass

            # User Subscriptions
            for usub in data.get("user_subscriptions", []):
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_subscriptions (user_id, is_premium, expires_at, stars_paid, updated_at)
                        VALUES (:user_id, :is_premium, :expires_at, :stars_paid, :updated_at)
                    ''', usub)
                except Exception:
                    pass

            # Chat Sniffer Settings
            for css in data.get("chat_sniffer_settings", []):
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO chat_sniffer_settings (chat_id, is_enabled, show_edits, show_deletions, notify_user_id, updated_at)
                        VALUES (:chat_id, :is_enabled, :show_edits, :show_deletions, :notify_user_id, :updated_at)
                    ''', css)
                except Exception:
                    pass

            # Sniffer Messages
            for sm in data.get("sniffer_messages", []):
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO sniffer_messages (chat_id, message_id, user_id, username, first_name, text, media_type, chat_title, created_at, file_id)
                        VALUES (:chat_id, :message_id, :user_id, :username, :first_name, :text, :media_type, :chat_title, :created_at, :file_id)
                    ''', sm)
                except Exception:
                    pass

            # Blocked Users
            for bu in data.get("blocked_users", []):
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO blocked_users (user_id, blocked_at, reason)
                        VALUES (:user_id, :blocked_at, :reason)
                    ''', bu)
                except Exception:
                    pass

            # Secretary Chat Modes (per-chat .a_troll/.girl/.anime overrides)
            for scm in data.get("secretary_chat_modes", []):
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO secretary_chat_modes (owner_id, chat_id, mode, updated_at)
                        VALUES (:owner_id, :chat_id, :mode, :updated_at)
                    ''', scm)
                except Exception:
                    pass

            # Secretary Chat Status (per-chat .bot on/off)
            for scs in data.get("secretary_chat_status", []):
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO secretary_chat_status (owner_id, chat_id, is_enabled, updated_at)
                        VALUES (:owner_id, :chat_id, :is_enabled, :updated_at)
                    ''', scs)
                except Exception:
                    pass

            # Business Connections (Telegram Business Secretary)
            for bc in data.get("business_connections", []):
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO business_connections (connection_id, user_id, user_chat_id, can_reply, is_enabled, secretary_mode, custom_prompt, auto_reply_all, ignored_chats, created_at, updated_at)
                        VALUES (:connection_id, :user_id, :user_chat_id, :can_reply, :is_enabled, :secretary_mode, :custom_prompt, :auto_reply_all, :ignored_chats, :created_at, :updated_at)
                    ''', bc)
                except Exception:
                    pass

            # Business Chats (Telegram Business Dialogues Mapping)
            for bch in data.get("business_chats", []):
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO business_chats (chat_id, business_connection_id, owner_id, contact_name, updated_at)
                        VALUES (:chat_id, :business_connection_id, :owner_id, :contact_name, :updated_at)
                    ''', bch)
                except Exception:
                    pass

            # Chat Automod settings (anti-mat, anti-links, warn_limit, etc.)
            for ca in data.get("chat_automod", []):
                try:
                    cols = list(ca.keys())
                    if cols:
                        col_str = ", ".join(cols)
                        ph_str = ", ".join([f":{c}" for c in cols])
                        cursor.execute(f'''
                            INSERT OR REPLACE INTO chat_automod ({col_str})
                            VALUES ({ph_str})
                        ''', ca)
                except Exception:
                    pass

            # Secretary Muted Chats (.mute)
            for scm in data.get("secretary_chat_mutes", []):
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO secretary_chat_mutes (owner_id, chat_id, is_muted, updated_at)
                        VALUES (:owner_id, :chat_id, :is_muted, :updated_at)
                    ''', scm)
                except Exception:
                    pass

            # Forum Topics (supergroup per-topic modes & automod)
            for ct in data.get("chat_topics", []):
                try:
                    cols = list(ct.keys())
                    if cols:
                        col_str = ", ".join(cols)
                        ph_str = ", ".join([f":{c}" for c in cols])
                        cursor.execute(f'''
                            INSERT OR REPLACE INTO chat_topics ({col_str})
                            VALUES ({ph_str})
                        ''', ct)
                except Exception:
                    pass

            # Chat Targets (.target / .a_troll)
            for ctg in data.get("chat_targets", []):
                try:
                    cols = list(ctg.keys())
                    if cols:
                        col_str = ", ".join(cols)
                        ph_str = ", ".join([f":{c}" for c in cols])
                        cursor.execute(f'''
                            INSERT OR REPLACE INTO chat_targets ({col_str})
                            VALUES ({ph_str})
                        ''', ctg)
                except Exception:
                    pass

            # User Always Online state
            for uao in data.get("user_always_online", []):
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_always_online (user_id, is_online, updated_at)
                        VALUES (:user_id, :is_online, :updated_at)
                    ''', uao)
                except Exception:
                    pass

            # Chat Moderation Configs (SQLite mirrored)
            for cmc in data.get("chat_moderation_config", []):
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO chat_moderation_config (chat_id, config_json, updated_at)
                        VALUES (:chat_id, :config_json, :updated_at)
                    ''', cmc)
                except Exception:
                    pass

            # Ensure Creator is set to evil if default or missing
            cursor.execute("INSERT OR REPLACE INTO user_settings (user_id, mode) VALUES (6363403785, COALESCE((SELECT CASE WHEN mode = 'default' THEN 'evil' ELSE mode END FROM user_settings WHERE user_id = 6363403785), 'evil'))")
            # Ensure groups never have evil mode
            cursor.execute("UPDATE user_settings SET mode = 'default' WHERE user_id < 0 AND mode = 'evil'")

            conn.commit()
            conn.close()
            logger.info("Persistent backup successfully restored to SQLite database!")

        # Restore and merge moderation data (rules, warns, custom roles, automod, staff)
        mod_chats_to_restore = {}
        if "moderation_data" in data and isinstance(data["moderation_data"], dict) and data["moderation_data"].get("chats"):
            mod_chats_to_restore.update(data["moderation_data"]["chats"])
        for cmc in data.get("chat_moderation_config", []):
            try:
                cid_k = str(cmc.get("chat_id"))
                if cid_k and cid_k not in mod_chats_to_restore:
                    mod_chats_to_restore[cid_k] = json.loads(cmc.get("config_json", "{}"))
            except Exception:
                pass

        if mod_chats_to_restore:
            try:
                mod_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "moderation_data.json")
                existing_chats = {}
                if os.path.exists(mod_json_path):
                    try:
                        with open(mod_json_path, "r", encoding="utf-8") as ef:
                            existing_chats = json.load(ef).get("chats", {})
                    except Exception:
                        pass
                
                # Merge remote with existing: NEVER erase custom rules or custom roles!
                merged = dict(existing_chats)
                for cid, c_cfg in mod_chats_to_restore.items():
                    if cid not in merged:
                        merged[cid] = c_cfg
                    else:
                        ex_r = merged[cid].get("rules", "")
                        rem_r = c_cfg.get("rules", "")
                        if "пока не установлены" in ex_r and rem_r and "пока не установлены" not in rem_r:
                            merged[cid]["rules"] = rem_r
                        elif rem_r and not ex_r:
                            merged[cid]["rules"] = rem_r
                        if c_cfg.get("custom_roles") and not merged[cid].get("custom_roles"):
                            merged[cid]["custom_roles"] = c_cfg["custom_roles"]
                        if c_cfg.get("warns") and not merged[cid].get("warns"):
                            merged[cid]["warns"] = c_cfg["warns"]
                        if c_cfg.get("admins") and not merged[cid].get("admins"):
                            merged[cid]["admins"] = c_cfg["admins"]
                        if c_cfg.get("moders") and not merged[cid].get("moders"):
                            merged[cid]["moders"] = c_cfg["moders"]

                with open(mod_json_path, "w", encoding="utf-8") as mf:
                    json.dump({"chats": merged}, mf, ensure_ascii=False, indent=2)

                # Mirror into SQLite chat_moderation_config table
                for cid, c_cfg in merged.items():
                    save_chat_moderation_config(cid, c_cfg)

                logger.info(f"Restored and merged {len(merged)} chat moderation configs from persistent backup!")
            except Exception as _re:
                logger.warning(f"Error restoring moderation_data: {_re}")
    except Exception as e:
        logger.warning(f"Error restoring persistent backup: {e}")

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=10000;")
    except Exception:
        pass
    return conn

def init_db():
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Table: users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_creator INTEGER DEFAULT 0,
                first_seen TEXT,
                last_seen TEXT,
                total_messages INTEGER DEFAULT 0
            )
        ''')

        # Table: blocked_users (Users blocked from Web Control Center or admin commands)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocked_users (
                user_id INTEGER PRIMARY KEY,
                blocked_at TEXT,
                reason TEXT DEFAULT ''
            )
        ''')

        # Ensure groups never have evil mode
        try:
            cursor.execute("UPDATE user_settings SET mode = 'default' WHERE user_id < 0 AND mode = 'evil'")
        except Exception:
            pass
        
        # Table: chats
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                chat_title TEXT,
                chat_type TEXT DEFAULT 'private',
                created_at TEXT,
                last_activity TEXT,
                message_count INTEGER DEFAULT 0
            )
        ''')
        try:
            cursor.execute("DELETE FROM chats WHERE chat_title LIKE 'Business:%' OR chat_type = 'business'")
        except Exception:
            pass
        
        # Table: messages
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                sender_type TEXT, -- 'user' or 'bot'
                sender_name TEXT,
                text TEXT,
                media_type TEXT DEFAULT 'text', -- 'text', 'photo', 'voice', 'audio', 'video', 'sticker', 'doc'
                media_info TEXT,
                timestamp TEXT,
                is_reply_to INTEGER
            )
        ''')
        
        # Table: user_economy
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_economy (
                user_id INTEGER PRIMARY KEY,
                reputation INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 1000,
                last_daily TEXT
            )
        ''')
        
        # Table: user_settings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                mode TEXT DEFAULT 'default',
                voice_style TEXT DEFAULT 'default'
            )
        ''')
        try:
            cursor.execute("ALTER TABLE user_settings ADD COLUMN voice_style TEXT DEFAULT 'default'")
        except Exception:
            pass

        # Table: user_subscriptions (Telegram Stars / Premium)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                user_id INTEGER PRIMARY KEY,
                is_premium INTEGER DEFAULT 0,
                expires_at TEXT,
                stars_paid INTEGER DEFAULT 0,
                updated_at TEXT
            )
        ''')

        # Table: daily_usage (Track daily queries/photos for non-premium limits)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_usage (
                user_id INTEGER,
                date_str TEXT,
                photos_count INTEGER DEFAULT 0,
                queries_count INTEGER DEFAULT 0,
                docs_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, date_str)
            )
        ''')
        
        # Table: scripts (Cloud Raw code and Lua / Git script hosting)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scripts (
                script_id TEXT PRIMARY KEY,
                title TEXT,
                language TEXT DEFAULT 'lua',
                code TEXT,
                author_id INTEGER,
                author_name TEXT,
                views INTEGER DEFAULT 0,
                created_at TEXT
            )
        ''')
        
        # Table: app_settings (Persistent key-value configuration, e.g. GITHUB_TOKEN)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        ''')
        
        # Table: chat_automod (Auto-Moderation: anti-mat, anti-18+, anti-nsfw-media, anti-links, anti-ai, custom warns/punishment)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_automod (
                chat_id INTEGER PRIMARY KEY,
                anti_mat INTEGER DEFAULT 1,
                anti_18plus INTEGER DEFAULT 1,
                anti_nsfw_media INTEGER DEFAULT 1,
                anti_links INTEGER DEFAULT 0,
                anti_ai INTEGER DEFAULT 1,
                exempt_admins INTEGER DEFAULT 0,
                action TEXT DEFAULT 'warn',
                warn_limit INTEGER DEFAULT 3,
                warn_punishment TEXT DEFAULT 'mute',
                punishment_duration TEXT DEFAULT '30m',
                updated_at TEXT
            )
        ''')
        for col_def in [
            ("anti_ai", "INTEGER DEFAULT 1"),
            ("exempt_admins", "INTEGER DEFAULT 0"),
            ("warn_limit", "INTEGER DEFAULT 3"),
            ("warn_punishment", "TEXT DEFAULT 'mute'"),
            ("punishment_duration", "TEXT DEFAULT '30m'"),
            ("anti_channels", "INTEGER DEFAULT 0"),
            ("anti_anonymous", "INTEGER DEFAULT 0")
        ]:
            try:
                cursor.execute(f"ALTER TABLE chat_automod ADD COLUMN {col_def[0]} {col_def[1]}")
            except Exception:
                pass
        
        # Table: learning_experience (Autonomous self-learning & error knowledge base)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_experience (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_signature TEXT UNIQUE,
                error_type TEXT,
                error_message TEXT,
                traceback_snippet TEXT,
                context_data TEXT,
                root_cause TEXT,
                solution TEXT,
                occurrence_count INTEGER DEFAULT 1,
                first_seen TEXT,
                last_seen TEXT,
                resolved INTEGER DEFAULT 0
            )
        ''')
        
        # Table: bot_admins (Appointed bot administrators)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                granted_by INTEGER,
                granted_at TEXT
            )
        ''')
        
        # Table: business_connections (Telegram Business AI Secretary)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS business_connections (
                connection_id TEXT PRIMARY KEY,
                user_id INTEGER,
                user_chat_id INTEGER,
                can_reply INTEGER DEFAULT 1,
                is_enabled INTEGER DEFAULT 1,
                secretary_mode TEXT DEFAULT 'assistant',
                custom_prompt TEXT DEFAULT '',
                auto_reply_all INTEGER DEFAULT 1,
                ignored_chats TEXT DEFAULT '[]',
                created_at TEXT,
                updated_at TEXT
            )
        ''')

        # Table: business_chats (Telegram Business Dialogues Mapping)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS business_chats (
                chat_id INTEGER PRIMARY KEY,
                business_connection_id TEXT,
                owner_id INTEGER,
                contact_name TEXT DEFAULT '',
                updated_at TEXT
            )
        ''')

        # Table: secretary_chat_status (Per-chat Secretary enabled state: .bot on / .bot off)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS secretary_chat_status (
                owner_id INTEGER,
                chat_id INTEGER,
                is_enabled INTEGER DEFAULT 1,
                updated_at TEXT,
                PRIMARY KEY (owner_id, chat_id)
            )
        ''')

        # Table: secretary_chat_mutes (Per-chat instant delete mute state: .mute)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS secretary_chat_mutes (
                owner_id INTEGER,
                chat_id INTEGER,
                is_muted INTEGER DEFAULT 1,
                updated_at TEXT,
                PRIMARY KEY (owner_id, chat_id)
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_business_chats_owner ON business_chats(owner_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_business_chats_conn ON business_chats(business_connection_id)')


        # Table: chat_targets (Group Chat Auto-Roast Targets)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_targets (
                chat_id INTEGER,
                target_user_id INTEGER,
                target_username TEXT DEFAULT '',
                added_by INTEGER,
                created_at TEXT,
                PRIMARY KEY (chat_id, target_user_id)
            )
        ''')

        # Table: sniffer_messages (Tracking messages for edit & delete sniffer)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sniffer_messages (
                chat_id INTEGER,
                message_id INTEGER,
                user_id INTEGER,
                username TEXT DEFAULT '',
                first_name TEXT DEFAULT '',
                text TEXT DEFAULT '',
                media_type TEXT DEFAULT 'text',
                created_at INTEGER,
                PRIMARY KEY (chat_id, message_id)
            )
        ''')

        # Table: sniffer_deleted_history (History of deleted messages in chat)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sniffer_deleted_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                message_id INTEGER,
                user_id INTEGER,
                username TEXT DEFAULT '',
                first_name TEXT DEFAULT '',
                text TEXT DEFAULT '',
                deleted_at TEXT
            )
        ''')

        # Table: chat_sniffer_settings (Anti-edit / Anti-delete toggle per chat)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sniffer_settings (
                chat_id INTEGER PRIMARY KEY,
                is_enabled INTEGER DEFAULT 1,
                show_edits INTEGER DEFAULT 1,
                show_deletions INTEGER DEFAULT 1,
                notify_user_id INTEGER DEFAULT NULL,
                updated_at TEXT
            )
        ''')

        # Migrations for sniffer tables
        try:
            cursor.execute('ALTER TABLE sniffer_messages ADD COLUMN chat_title TEXT DEFAULT ""')
        except Exception:
            pass
        try:
            cursor.execute('ALTER TABLE sniffer_deleted_history ADD COLUMN chat_title TEXT DEFAULT ""')
        except Exception:
            pass
        try:
            cursor.execute('ALTER TABLE chat_sniffer_settings ADD COLUMN notify_user_id INTEGER DEFAULT NULL')
        except Exception:
            pass
        try:
            cursor.execute('ALTER TABLE sniffer_messages ADD COLUMN file_id TEXT DEFAULT ""')
        except Exception:
            pass
        try:
            cursor.execute('ALTER TABLE sniffer_deleted_history ADD COLUMN file_id TEXT DEFAULT ""')
        except Exception:
            pass
        try:
            cursor.execute('ALTER TABLE sniffer_deleted_history ADD COLUMN media_type TEXT DEFAULT "text"')
        except Exception:
            pass

        # Table: code_backups (Self-Evolution & Rollback snapshots)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_id TEXT UNIQUE,
                timestamp TEXT,
                commit_hash TEXT,
                description TEXT,
                target_files TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT
            )
        ''')

        # Table: chat_topics (Per-topic AI modes and per-topic automod filters in Telegram forum supergroups)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_topics (
                chat_id INTEGER,
                thread_id INTEGER,
                title TEXT DEFAULT '',
                mode TEXT DEFAULT NULL,
                automod_enabled INTEGER DEFAULT 1,
                anti_mat INTEGER DEFAULT NULL,
                anti_18plus INTEGER DEFAULT NULL,
                anti_nsfw_media INTEGER DEFAULT NULL,
                anti_links INTEGER DEFAULT NULL,
                anti_ai INTEGER DEFAULT NULL,
                exempt_admins INTEGER DEFAULT NULL,
                action TEXT DEFAULT NULL,
                warn_limit INTEGER DEFAULT NULL,
                warn_punishment TEXT DEFAULT NULL,
                punishment_duration TEXT DEFAULT NULL,
                rules TEXT DEFAULT NULL,
                created_at TEXT,
                updated_at TEXT,
                PRIMARY KEY (chat_id, thread_id)
            )
        ''')

        # Ensure all columns exist in chat_topics if table was already created earlier
        for col_def in [
            ("anti_nsfw_media", "INTEGER DEFAULT NULL"),
            ("exempt_admins", "INTEGER DEFAULT NULL"),
            ("action", "TEXT DEFAULT NULL"),
            ("warn_limit", "INTEGER DEFAULT NULL"),
            ("warn_punishment", "TEXT DEFAULT NULL"),
            ("punishment_duration", "TEXT DEFAULT NULL"),
            ("anti_mat", "INTEGER DEFAULT NULL"),
            ("anti_18plus", "INTEGER DEFAULT NULL"),
            ("anti_links", "INTEGER DEFAULT NULL"),
            ("anti_ai", "INTEGER DEFAULT NULL"),
            ("automod_enabled", "INTEGER DEFAULT 1"),
            ("mode", "TEXT DEFAULT NULL"),
            ("rules", "TEXT DEFAULT NULL"),
            ("title", "TEXT DEFAULT ''"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE chat_topics ADD COLUMN {col_def[0]} {col_def[1]}")
            except Exception:
                pass

        # Indexes for fast search & retrieval
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_usage_date ON daily_usage(date_str)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scripts_created ON scripts(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_learning_signature ON learning_experience(error_signature)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bot_admins_uid ON bot_admins(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_business_user_id ON business_connections(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_code_backups_bid ON code_backups(backup_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_topics_cid_tid ON chat_topics(chat_id, thread_id)')

        # Table: chat_moderation_config (Mirrors moderation_data.json for instant SQLite recovery across deploys)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_moderation_config (
                chat_id TEXT PRIMARY KEY,
                config_json TEXT,
                updated_at TEXT
            )
        ''')
        
        # Table: user_economy columns migration if needed
        try:
            cursor.execute("ALTER TABLE user_economy ADD COLUMN last_work TEXT")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE user_economy ADD COLUMN inventory TEXT DEFAULT '[]'")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE sniffer_messages ADD COLUMN business_connection_id TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE sniffer_messages ADD COLUMN owner_user_id INTEGER DEFAULT 0")
        except Exception:
            pass

        # Clean up existing chats where title got polluted with 'AI for copil'
        try:
            cursor.execute('''
                UPDATE chats
                SET chat_title = (
                    SELECT COALESCE(
                        NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''),
                        NULLIF('@' || u.username, '@'),
                        'User ' || chats.chat_id
                    )
                    FROM users u
                    WHERE u.user_id = chats.chat_id
                )
                WHERE chats.chat_type = 'private' AND (chats.chat_title = 'AI for copil' OR chats.chat_title IS NULL OR chats.chat_title = '')
            ''')
        except Exception as e:
            logger.warning(f"Error cleaning chats titles: {e}")

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {DB_PATH}")

    # Restore from persistent backup (survives Render dyno restarts / rebuilds)
    restore_persistent_backup()

    # Ensure all business connections are enabled
    try:
        with _db_lock:
            _u_conn = get_connection()
            _u_cur = _u_conn.cursor()
            _u_cur.execute("UPDATE business_connections SET is_enabled = 1 WHERE is_enabled = 0")
            _u_conn.commit()
            _u_conn.close()
    except Exception as ub_err:
        logger.debug(f"Could not ensure business connections enabled: {ub_err}")

    # Import any known users from moderation_data.json and messages
    sync_users_from_moderation()

    # Always ensure Creator mode is 'evil' (never 'default')
    set_user_mode(6363403785, "evil")

    # Persist snapshot
    save_persistent_backup(force=True)

def register_user(user, is_creator=False):
    """Safely registers or updates a user in the SQLite users table and ensures economy record."""
    if not user:
        return
    user_id = getattr(user, 'id', None)
    if not user_id:
        return
    username = getattr(user, 'username', '') or ""
    first_name = getattr(user, 'first_name', '') or ""
    last_name = getattr(user, 'last_name', '') or ""
    if user_id == 6363403785 or "k3rnel" in (username.lower() if username else ""):
        is_creator = True
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name, is_creator, first_seen, last_seen, total_messages)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = COALESCE(NULLIF(excluded.username, ''), users.username),
                    first_name = COALESCE(NULLIF(excluded.first_name, ''), users.first_name),
                    last_name = COALESCE(NULLIF(excluded.last_name, ''), users.last_name),
                    is_creator = MAX(users.is_creator, excluded.is_creator),
                    last_seen = excluded.last_seen
            ''', (user_id, username, first_name, last_name, 1 if is_creator else 0, now, now))
            cursor.execute("INSERT OR IGNORE INTO user_economy (user_id, reputation, coins) VALUES (?, 0, 1000)", (user_id,))
            conn.commit()
        except Exception as e:
            logger.error(f"Error in register_user: {e}")
        finally:
            conn.close()

def sync_users_from_moderation():
    """Imports users and chats saved in moderation_data.json and messages into SQLite database."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            if os.path.exists(MODERATION_JSON_PATH):
                with open(MODERATION_JSON_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                chats_data = data.get("chats", {}) if "chats" in data else data
                for chat_id_str, chat_info in chats_data.items():
                    if not isinstance(chat_info, dict):
                        continue
                    try:
                        cid = int(chat_id_str)
                        ctitle = chat_info.get("title", "") or (f"Group {cid}" if cid < 0 else f"User {cid}")
                        ctype = "supergroup" if cid < 0 else "private"
                        cursor.execute('''
                            INSERT INTO chats (chat_id, chat_title, chat_type, created_at, last_activity, message_count)
                            VALUES (?, ?, ?, ?, ?, 1)
                            ON CONFLICT(chat_id) DO UPDATE SET
                                chat_title = CASE WHEN excluded.chat_title != '' AND chats.chat_title = '' THEN excluded.chat_title ELSE chats.chat_title END
                        ''', (cid, ctitle, ctype, now, now))
                    except Exception:
                        pass

                    users_map = chat_info.get("users", {})
                    for uid_str, u in users_map.items():
                        try:
                            uid = int(uid_str)
                            uname = u.get("username", "") or ""
                            name = u.get("name", "") or f"User {uid}"
                            is_creator = 1 if (uid == 6363403785 or "k3rnel" in uname.lower()) else 0
                            cursor.execute('''
                                INSERT INTO users (user_id, username, first_name, last_name, is_creator, first_seen, last_seen, total_messages)
                                VALUES (?, ?, ?, '', ?, ?, ?, 1)
                                ON CONFLICT(user_id) DO UPDATE SET
                                    username = COALESCE(NULLIF(excluded.username, ''), users.username),
                                    first_name = COALESCE(NULLIF(excluded.first_name, ''), users.first_name),
                                    is_creator = MAX(users.is_creator, excluded.is_creator)
                            ''', (uid, uname, name, is_creator, now, now))
                            cursor.execute("INSERT OR IGNORE INTO user_economy (user_id, reputation, coins) VALUES (?, 0, 1000)", (uid,))
                        except Exception:
                            continue

                    # Sync admins / moders / warns
                    for role_group in ["admins", "moders", "warns"]:
                        group_map = chat_info.get(role_group, {})
                        if isinstance(group_map, dict):
                            for r_uid_str, r_u in group_map.items():
                                try:
                                    r_uid = int(r_uid_str)
                                    r_uname = ""
                                    r_name = f"User {r_uid}"
                                    if isinstance(r_u, dict):
                                        r_uname = r_u.get("username", "") or ""
                                        r_name = r_u.get("name", "") or r_name
                                    elif isinstance(r_u, str):
                                        r_name = r_u
                                    is_c = 1 if (r_uid == 6363403785 or "k3rnel" in r_uname.lower()) else 0
                                    cursor.execute('''
                                        INSERT INTO users (user_id, username, first_name, last_name, is_creator, first_seen, last_seen, total_messages)
                                        VALUES (?, ?, ?, '', ?, ?, ?, 1)
                                        ON CONFLICT(user_id) DO UPDATE SET
                                            username = COALESCE(NULLIF(excluded.username, ''), users.username),
                                            first_name = COALESCE(NULLIF(excluded.first_name, ''), users.first_name),
                                            is_creator = MAX(users.is_creator, excluded.is_creator)
                                    ''', (r_uid, r_uname, r_name, is_c, now, now))
                                    cursor.execute("INSERT OR IGNORE INTO user_economy (user_id, reputation, coins) VALUES (?, 0, 1000)", (r_uid,))
                                except Exception:
                                    continue

                    # Sync chat owner
                    owner_id = chat_info.get("owner_id")
                    if owner_id:
                        try:
                            o_uid = int(owner_id)
                            o_uname = chat_info.get("owner_username", "") or ""
                            o_name = chat_info.get("owner_name", "") or f"User {o_uid}"
                            is_c = 1 if (o_uid == 6363403785 or "k3rnel" in o_uname.lower()) else 0
                            cursor.execute('''
                                INSERT INTO users (user_id, username, first_name, last_name, is_creator, first_seen, last_seen, total_messages)
                                VALUES (?, ?, ?, '', ?, ?, ?, 1)
                                ON CONFLICT(user_id) DO UPDATE SET
                                    username = COALESCE(NULLIF(excluded.username, ''), users.username),
                                    first_name = COALESCE(NULLIF(excluded.first_name, ''), users.first_name),
                                    is_creator = MAX(users.is_creator, excluded.is_creator)
                            ''', (o_uid, o_uname, o_name, is_c, now, now))
                            cursor.execute("INSERT OR IGNORE INTO user_economy (user_id, reputation, coins) VALUES (?, 0, 1000)", (o_uid,))
                        except Exception:
                            pass

            # Also sync any user_id from messages table
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name, is_creator, first_seen, last_seen, total_messages)
                SELECT 
                    m.user_id,
                    '',
                    COALESCE(NULLIF(m.sender_name, ''), 'User ' || m.user_id),
                    '',
                    CASE WHEN m.user_id = 6363403785 THEN 1 ELSE 0 END,
                    MIN(m.timestamp),
                    MAX(m.timestamp),
                    COUNT(m.id)
                FROM messages m
                WHERE m.user_id IS NOT NULL AND m.user_id > 0
                GROUP BY m.user_id
                ON CONFLICT(user_id) DO UPDATE SET
                    first_name = CASE WHEN users.first_name = '' OR users.first_name LIKE 'User %' THEN excluded.first_name ELSE users.first_name END,
                    total_messages = MAX(users.total_messages, excluded.total_messages),
                    last_seen = MAX(users.last_seen, excluded.last_seen)
            ''')

            # Also sync private and group chats from messages table into chats table
            cursor.execute('''
                INSERT INTO chats (chat_id, chat_title, chat_type, created_at, last_activity, message_count)
                SELECT 
                    m.chat_id,
                    CASE WHEN m.chat_id > 0 THEN 'User ' || m.chat_id ELSE 'Group ' || m.chat_id END,
                    CASE WHEN m.chat_id > 0 THEN 'private' ELSE 'supergroup' END,
                    MIN(m.timestamp),
                    MAX(m.timestamp),
                    COUNT(m.id)
                FROM messages m
                WHERE m.chat_id IS NOT NULL
                GROUP BY m.chat_id
                ON CONFLICT(chat_id) DO UPDATE SET
                    last_activity = MAX(chats.last_activity, excluded.last_activity),
                    message_count = MAX(chats.message_count, excluded.message_count)
            ''')

            # Also sync private chats to users table
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name, is_creator, first_seen, last_seen, total_messages)
                SELECT 
                    c.chat_id,
                    '',
                    COALESCE(NULLIF(c.chat_title, ''), 'User ' || c.chat_id),
                    '',
                    CASE WHEN c.chat_id = 6363403785 THEN 1 ELSE 0 END,
                    c.created_at,
                    c.last_activity,
                    c.message_count
                FROM chats c
                WHERE c.chat_id > 0
                ON CONFLICT(user_id) DO UPDATE SET
                    first_name = CASE WHEN users.first_name = '' OR users.first_name LIKE 'User %' THEN excluded.first_name ELSE users.first_name END
            ''')

            # Sync from economy and subscriptions
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, is_creator, first_seen, last_seen, total_messages)
                SELECT user_id, '', 'User ' || user_id, '', CASE WHEN user_id = 6363403785 THEN 1 ELSE 0 END, ?, ?, 1
                FROM user_economy
            ''', (now, now))

            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, is_creator, first_seen, last_seen, total_messages)
                SELECT user_id, '', 'User ' || user_id, '', CASE WHEN user_id = 6363403785 THEN 1 ELSE 0 END, ?, ?, 1
                FROM user_subscriptions
            ''', (now, now))

            # Sync from business connections
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, is_creator, first_seen, last_seen, total_messages)
                    SELECT user_id, '', 'Business User ' || user_id, '', CASE WHEN user_id = 6363403785 THEN 1 ELSE 0 END, created_at, updated_at, 1
                    FROM business_connections
                    WHERE user_id IS NOT NULL AND user_id > 0
                ''')
            except Exception:
                pass

            # Sync from bot admins
            try:
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, is_creator, first_seen, last_seen, total_messages)
                    SELECT user_id, username, first_name, '', CASE WHEN user_id = 6363403785 THEN 1 ELSE 0 END, granted_at, granted_at, 1
                    FROM bot_admins
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = COALESCE(NULLIF(excluded.username, ''), users.username),
                        first_name = COALESCE(NULLIF(excluded.first_name, ''), users.first_name)
                ''')
            except Exception:
                pass

            # Ensure all users have user_economy entries
            cursor.execute('''
                INSERT OR IGNORE INTO user_economy (user_id, reputation, coins)
                SELECT user_id, 0, 1000 FROM users
            ''')

            conn.commit()
        except Exception as e:
            logger.warning(f"Error syncing moderation users to DB: {e}")
        finally:
            conn.close()

def log_message(chat_id, user_id, sender_type, sender_name, text, media_type='text', media_info=None, chat_title=None, chat_type='private', user_obj=None, is_creator=False):
    """
    Thread-safely logs a message and updates user and chat stats.
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # 1. Update/Insert User (if user_obj or user_id provided)
            if user_id and sender_type == 'user':
                username = ""
                first_name = sender_name or ""
                last_name = ""
                if user_obj:
                    username = getattr(user_obj, 'username', '') or ""
                    first_name = getattr(user_obj, 'first_name', '') or ""
                    last_name = getattr(user_obj, 'last_name', '') or ""
                    if getattr(user_obj, 'id', 0) == 6363403785 or "k3rnel" in (username.lower() if username else ""):
                        is_creator = True
                elif user_id == 6363403785:
                    is_creator = True

                creator_val = 1 if is_creator else 0
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, is_creator, first_seen, last_seen, total_messages)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = COALESCE(NULLIF(excluded.username, ''), users.username),
                        first_name = COALESCE(NULLIF(excluded.first_name, ''), users.first_name),
                        last_name = COALESCE(NULLIF(excluded.last_name, ''), users.last_name),
                        is_creator = MAX(users.is_creator, excluded.is_creator),
                        last_seen = excluded.last_seen,
                        total_messages = users.total_messages + 1
                ''', (user_id, username, first_name, last_name, creator_val, now, now))
                cursor.execute("INSERT OR IGNORE INTO user_economy (user_id, reputation, coins) VALUES (?, 0, 1000)", (user_id,))

            # 2. Update/Insert Chat
            if sender_type == 'user':
                user_title = (f"{getattr(user_obj, 'first_name', '')} {getattr(user_obj, 'last_name', '')}".strip() if user_obj else "") or (f"@{getattr(user_obj, 'username', '')}" if (user_obj and getattr(user_obj, 'username', '')) else sender_name)
            else:
                user_title = ""

            title = chat_title or user_title
            if not title or title == "AI for copil":
                if chat_type == 'private':
                    title = f"User {chat_id}"
                else:
                    title = f"Group {chat_id}"

            cursor.execute('''
                INSERT INTO chats (chat_id, chat_title, chat_type, created_at, last_activity, message_count)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(chat_id) DO UPDATE SET
                    chat_title = CASE 
                        WHEN excluded.chat_title != '' AND excluded.chat_title != 'AI for copil' THEN excluded.chat_title 
                        ELSE chats.chat_title 
                    END,
                    chat_type = excluded.chat_type,
                    last_activity = excluded.last_activity,
                    message_count = chats.message_count + 1
            ''', (chat_id, title, chat_type, now, now))

            # 3. Insert Message
            cursor.execute('''
                INSERT INTO messages (chat_id, user_id, sender_type, sender_name, text, media_type, media_info, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (chat_id, user_id, sender_type, sender_name, text or "", media_type, media_info, now))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to log message: {e}")
        finally:
            conn.close()

    # Throttled persistent backup save so all messages survive restarts
    try:
        save_persistent_backup(force=False)
    except Exception:
        pass

def get_all_chats(only_bot_users=False, chat_type=None):
    """
    Returns a list of all chats ordered by latest activity with last message preview and user metadata.
    If only_bot_users is True, strictly returns chats with actual bot users (filtering out third-party business chats).
    """
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        conditions = [
            "(bc.business_connection_id IS NULL OR bc.business_connection_id = '')",
            "c.chat_type != 'business'",
            "(c.chat_title NOT LIKE 'Business:%')"
        ]
        if only_bot_users or chat_type in ['private', 'users']:
            conditions.append("c.chat_type = 'private' AND c.chat_id > 0")
        elif chat_type in ['group', 'groups']:
            conditions.append("(c.chat_type != 'private' OR c.chat_id < 0)")
        where_clause = "WHERE " + " AND ".join(conditions)

        query = f'''
            SELECT 
                c.chat_id,
                c.chat_title,
                c.chat_type,
                c.created_at,
                c.last_activity,
                c.message_count,
                m.text AS last_message_text,
                m.sender_name AS last_sender_name,
                m.sender_type AS last_sender_type,
                m.media_type AS last_media_type,
                m.timestamp AS last_message_time,
                u.username,
                u.first_name,
                u.last_name,
                u.is_creator,
                u.last_seen AS user_last_seen,
                s.is_premium,
                s.expires_at,
                bc.business_connection_id,
                bc.owner_id AS business_owner_id,
                bu.username AS business_owner_username,
                bu.first_name AS business_owner_first_name
            FROM chats c
            LEFT JOIN (
                SELECT m1.*
                FROM messages m1
                INNER JOIN (
                    SELECT chat_id, MAX(id) AS max_id
                    FROM messages
                    GROUP BY chat_id
                ) m2 ON m1.id = m2.max_id
            ) m ON c.chat_id = m.chat_id
            LEFT JOIN users u ON (c.chat_type = 'private' AND c.chat_id = u.user_id)
            LEFT JOIN user_subscriptions s ON (c.chat_type = 'private' AND c.chat_id = s.user_id)
            LEFT JOIN business_chats bc ON c.chat_id = bc.chat_id
            LEFT JOIN users bu ON bc.owner_id = bu.user_id
            {where_clause}
            ORDER BY c.last_activity DESC
        '''
        cursor.execute(query)
        rows = cursor.fetchall()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        chats = []
        for r in rows:
            is_c = bool(r["is_creator"] or (r["username"] and "k3rnel" in r["username"].lower()) or r["chat_id"] == 6363403785)
            is_prem = is_c or bool(r["is_premium"] == 1 and r["expires_at"] and r["expires_at"] > now_str)
            
            # Real display title (Never 'AI for copil' for user chats)
            if r["chat_type"] == "private":
                full_name = f"{r['first_name'] or ''} {r['last_name'] or ''}".strip()
                if full_name:
                    display_title = full_name
                elif r["username"]:
                    display_title = f"@{r['username']}"
                elif r["chat_title"] and r["chat_title"] != "AI for copil":
                    display_title = r["chat_title"]
                else:
                    display_title = f"User {r['chat_id']}"
            else:
                display_title = r["chat_title"] if (r["chat_title"] and r["chat_title"] != "AI for copil") else f"Group {r['chat_id']}"

            chats.append({
                "chat_id": r["chat_id"],
                "chat_title": display_title,
                "chat_type": r["chat_type"],
                "created_at": r["created_at"],
                "last_activity": r["last_activity"],
                "last_seen": r["user_last_seen"] or r["last_activity"],
                "message_count": r["message_count"],
                "last_message": {
                    "text": r["last_message_text"] or "",
                    "sender_name": r["last_sender_name"] or "",
                    "sender_type": r["last_sender_type"] or "bot",
                    "media_type": r["last_media_type"] or "text",
                    "timestamp": r["last_message_time"] or r["last_activity"]
                },
                "username": r["username"] or "",
                "first_name": r["first_name"] or "",
                "last_name": r["last_name"] or "",
                "is_creator": is_c,
                "is_premium": is_prem,
                "is_business": bool(r["chat_type"] == "business" or ("business_connection_id" in r.keys() and r["business_connection_id"])),
                "business_connection_id": (r["business_connection_id"] or "") if "business_connection_id" in r.keys() else "",
                "business_owner_id": r["business_owner_id"] if "business_owner_id" in r.keys() else None,
                "business_owner_name": (r["business_owner_first_name"] or r["business_owner_username"] or "") if "business_owner_first_name" in r.keys() else ""
            })
        conn.close()
        return chats

def get_bot_user_chats(limit=10, offset=0):
    """Returns paginated list of chats with real bot users for Telegram inline creator panel."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            query = '''
                SELECT 
                    c.chat_id,
                    c.chat_title,
                    c.last_activity,
                    c.message_count,
                    u.username,
                    u.first_name,
                    u.last_name,
                    u.is_creator,
                    m.text AS last_message_text,
                    m.sender_name AS last_sender_name,
                    m.timestamp AS last_message_time
                FROM chats c
                JOIN users u ON c.chat_id = u.user_id
                LEFT JOIN (
                    SELECT m1.*
                    FROM messages m1
                    INNER JOIN (
                        SELECT chat_id, MAX(id) AS max_id
                        FROM messages
                        GROUP BY chat_id
                    ) m2 ON m1.id = m2.max_id
                ) m ON c.chat_id = m.chat_id
                WHERE c.chat_type = 'private' AND c.chat_id > 0
                ORDER BY c.last_activity DESC
                LIMIT ? OFFSET ?
            '''
            cursor.execute(query, (int(limit), int(offset)))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error in get_bot_user_chats: {e}")
            return []
        finally:
            conn.close()

def get_total_bot_user_chats() -> int:
    """Returns total count of chats with real bot users for pagination."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT COUNT(*) AS total
                FROM chats c
                JOIN users u ON c.chat_id = u.user_id
                WHERE c.chat_type = 'private' AND c.chat_id > 0
            ''')
            row = cursor.fetchone()
            return row['total'] if row else 0
        except Exception as e:
            logger.error(f"Error in get_total_bot_user_chats: {e}")
            return 0
        finally:
            conn.close()

def get_all_users():
    """
    Returns full list of all bot users with stats, economy, subscription and daily limits.
    """
    sync_users_from_moderation()

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.user_id, u.username, u.first_name, u.last_name, u.is_creator, u.first_seen, u.last_seen, u.total_messages,
                   COALESCE(e.coins, 1000) AS coins, COALESCE(e.reputation, 0) AS reputation,
                   s.is_premium, s.expires_at, s.stars_paid,
                   d.photos_count, d.queries_count, d.docs_count,
                   us.mode,
                   CASE WHEN ba.user_id IS NOT NULL OR u.is_creator = 1 OR u.user_id = 6363403785 THEN 1 ELSE 0 END AS is_admin,
                   CASE WHEN bu.user_id IS NOT NULL THEN 1 ELSE 0 END AS is_blocked
            FROM users u
            LEFT JOIN user_economy e ON u.user_id = e.user_id
            LEFT JOIN user_subscriptions s ON u.user_id = s.user_id
            LEFT JOIN daily_usage d ON (u.user_id = d.user_id AND d.date_str = ?)
            LEFT JOIN user_settings us ON u.user_id = us.user_id
            LEFT JOIN bot_admins ba ON u.user_id = ba.user_id
            LEFT JOIN blocked_users bu ON u.user_id = bu.user_id
            ORDER BY u.is_creator DESC, is_admin DESC, u.last_seen DESC
        ''', (today_str,))
        rows = cursor.fetchall()
        
        users = []
        for r in rows:
            is_c = bool(r["is_creator"] or (r["username"] and "k3rnel" in r["username"].lower()) or r["user_id"] == 6363403785)
            full_name = ((r["first_name"] or "") + (" " + r["last_name"] if r["last_name"] else "")).strip() or (f"@{r['username']}" if r["username"] else f"User {r['user_id']}")
            
            is_prem = is_c or bool(r["is_premium"] == 1 and r["expires_at"] and r["expires_at"] > now_str)
            days_left = 9999 if is_c else 0
            if is_prem and not is_c and r["expires_at"]:
                try:
                    exp_dt = datetime.datetime.strptime(r["expires_at"], "%Y-%m-%d %H:%M:%S")
                    days_left = max(1, (exp_dt - datetime.datetime.now()).days + 1)
                except Exception:
                    pass

            u_mode = r["mode"] or ("evil" if is_c else "default")
            is_adm = bool(r["is_admin"])
            is_blk = bool(r["is_blocked"]) and not is_c

            users.append({
                "user_id": r["user_id"],
                "username": r["username"] or "",
                "full_name": full_name,
                "first_name": r["first_name"] or "",
                "last_name": r["last_name"] or "",
                "is_creator": is_c,
                "is_admin": is_adm,
                "is_blocked": is_blk,
                "mode": u_mode,
                "is_premium": is_prem,
                "expires_at": r["expires_at"] if not is_c else "Навсегда",
                "days_left": days_left,
                "first_seen": r["first_seen"],
                "last_seen": r["last_seen"],
                "total_messages": r["total_messages"],
                "coins": r["coins"],
                "reputation": r["reputation"],
                "photos_today": r["photos_count"] or 0,
                "queries_today": r["queries_count"] or 0,
                "docs_today": r["docs_count"] or 0
            })
        conn.close()
        return users

def revoke_user_premium(user_id):
    """Revokes Premium subscription for user."""
    if not user_id:
        return False
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return False

    user_premium_cache.set(uid, False)

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE user_subscriptions 
                SET is_premium = 0, expires_at = NULL 
                WHERE user_id = ?
            ''', (uid,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error revoking premium: {e}")
            return False
        finally:
            conn.close()

def get_chat_messages(chat_id, limit=1000):
    """
    Retrieves latest message history for a given chat ID in chronological order.
    """
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        if limit and limit > 0:
            cursor.execute('''
                SELECT id, chat_id, user_id, sender_type, sender_name, text, media_type, media_info, timestamp
                FROM (
                    SELECT id, chat_id, user_id, sender_type, sender_name, text, media_type, media_info, timestamp
                    FROM messages
                    WHERE chat_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                ORDER BY id ASC
            ''', (chat_id, limit))
        else:
            cursor.execute('''
                SELECT id, chat_id, user_id, sender_type, sender_name, text, media_type, media_info, timestamp
                FROM messages
                WHERE chat_id = ?
                ORDER BY id ASC
            ''', (chat_id,))
        rows = cursor.fetchall()
        
        messages = []
        for r in rows:
            messages.append({
                "id": r["id"],
                "chat_id": r["chat_id"],
                "user_id": r["user_id"],
                "sender_type": r["sender_type"],
                "sender_name": r["sender_name"],
                "text": r["text"],
                "media_type": r["media_type"],
                "media_info": r["media_info"],
                "timestamp": r["timestamp"]
            })
        conn.close()
        return messages

def delete_chat_messages(chat_id):
    """
    Clears message logs for a given chat ID.
    """
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM messages WHERE chat_id = ?', (chat_id,))
        cursor.execute('UPDATE chats SET message_count = 0 WHERE chat_id = ?', (chat_id,))
        conn.commit()
        conn.close()

def get_dashboard_stats():
    """
    Returns summary statistics for the web dashboard.
    """
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) AS total_users FROM users')
        total_users = cursor.fetchone()['total_users']
        
        cursor.execute('SELECT COUNT(*) AS total_chats FROM chats')
        total_chats = cursor.fetchone()['total_chats']
        
        cursor.execute('SELECT COUNT(*) AS total_messages FROM messages')
        total_messages = cursor.fetchone()['total_messages']
        
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) AS today_messages FROM messages WHERE timestamp LIKE ?", (f"{today}%",))
        today_messages = cursor.fetchone()['today_messages']
        
        cursor.execute("SELECT COUNT(*) AS private_chats FROM chats WHERE chat_type = 'private'")
        private_chats = cursor.fetchone()['private_chats']
        
        cursor.execute("SELECT COUNT(*) AS group_chats FROM chats WHERE chat_type != 'private'")
        group_chats = cursor.fetchone()['group_chats']
        
        conn.close()
        return {
            "total_users": total_users,
            "total_chats": total_chats,
            "private_chats": private_chats,
            "group_chats": group_chats,
            "total_messages": total_messages,
            "today_messages": today_messages,
            "status": "online",
            "creator": "k3rnel (6363403785)"
        }

def search_messages(query, limit=50):
    """
    Searches across all messages and user names.
    """
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        like_q = f"%{query}%"
        cursor.execute('''
            SELECT m.id, m.chat_id, m.user_id, m.sender_type, m.sender_name, m.text, m.media_type, m.timestamp, c.chat_title, c.chat_type
            FROM messages m
            LEFT JOIN chats c ON m.chat_id = c.chat_id
            WHERE m.text LIKE ? OR m.sender_name LIKE ? OR c.chat_title LIKE ?
            ORDER BY m.id DESC
            LIMIT ?
        ''', (like_q, like_q, like_q, limit))
        rows = cursor.fetchall()
        
        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "chat_id": r["chat_id"],
                "chat_title": r["chat_title"] or f"Chat {r['chat_id']}",
                "chat_type": r["chat_type"],
                "sender_name": r["sender_name"],
                "sender_type": r["sender_type"],
                "text": r["text"],
                "media_type": r["media_type"],
                "timestamp": r["timestamp"]
            })
        conn.close()
        return results

def get_chat_activity_top(chat_id, days=1, limit=10):
    """
    Returns top active users in a chat for the given period (days).
    If days is None or 0: queries all time.
    Calculates total messages, texts, stickers/gifs, other media, and user reputation.
    """
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        where_time = ""
        params = [chat_id]
        if days and days > 0:
            since_dt = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            where_time = "AND m.timestamp >= ?"
            params.append(since_dt)
            
        params.append(limit)
        
        query = f'''
            SELECT 
                m.user_id,
                COALESCE(
                    NULLIF(TRIM(COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, '')), ''),
                    NULLIF(u.username, ''),
                    NULLIF(m.sender_name, ''),
                    'Участник'
                ) AS name,
                COALESCE(ue.reputation, 0) AS rep,
                COUNT(*) AS total_msgs,
                SUM(CASE WHEN m.media_type = 'text' OR m.media_type IS NULL OR m.media_type = '' THEN 1 ELSE 0 END) AS text_msgs,
                SUM(CASE WHEN m.media_type IN ('sticker', 'animation', 'gif') THEN 1 ELSE 0 END) AS sticker_msgs,
                SUM(CASE WHEN m.media_type NOT IN ('text', 'sticker', 'animation', 'gif') AND m.media_type IS NOT NULL AND m.media_type != '' THEN 1 ELSE 0 END) AS media_msgs
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.user_id
            LEFT JOIN user_economy ue ON m.user_id = ue.user_id
            WHERE m.chat_id = ? AND m.sender_type = 'user' AND m.user_id IS NOT NULL {where_time}
            GROUP BY m.user_id
            ORDER BY total_msgs DESC
            LIMIT ?
        '''
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        
        top = []
        for r in rows:
            top.append({
                "user_id": r["user_id"],
                "name": r["name"],
                "rep": r["rep"],
                "total_msgs": r["total_msgs"],
                "text_msgs": r["text_msgs"] or 0,
                "sticker_msgs": r["sticker_msgs"] or 0,
                "media_msgs": r["media_msgs"] or 0,
                "msg_count": r["total_msgs"]
            })
        conn.close()
        return top

def get_chat_top_users(chat_id, limit=10):
    """Returns top active users in a specific chat by message count (all time)."""
    return get_chat_activity_top(chat_id, days=None, limit=limit)

def get_chat_stats_summary(chat_id):
    """Returns detailed statistics for a group chat."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT message_count, chat_title, created_at, last_activity FROM chats WHERE chat_id = ?', (chat_id,))
        chat_row = cursor.fetchone()
        
        cursor.execute('SELECT COUNT(DISTINCT user_id) AS active_users FROM messages WHERE chat_id = ? AND sender_type = "user"', (chat_id,))
        users_count = cursor.fetchone()['active_users']
        
        cursor.execute('SELECT COUNT(*) AS voice_count FROM messages WHERE chat_id = ? AND media_type = "voice"', (chat_id,))
        voice_count = cursor.fetchone()['voice_count']
        
        cursor.execute('SELECT COUNT(*) AS photo_count FROM messages WHERE chat_id = ? AND media_type = "photo"', (chat_id,))
        photo_count = cursor.fetchone()['photo_count']
        
        conn.close()
        return {
            "title": chat_row['chat_title'] if chat_row else "Чат",
            "total_messages": chat_row['message_count'] if chat_row else 0,
            "active_users": users_count,
            "voice_count": voice_count,
            "photo_count": photo_count,
            "created_at": chat_row['created_at'] if chat_row else "",
            "last_activity": chat_row['last_activity'] if chat_row else ""
        }

def get_user_economy(user_id):
    """Returns (reputation, coins) for a user."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT reputation, coins FROM user_economy WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT OR IGNORE INTO user_economy (user_id, reputation, coins) VALUES (?, 0, 1000)", (user_id,))
            conn.commit()
            conn.close()
            return 0, 1000
        conn.close()
        return row['reputation'], row['coins']

def change_user_rep(user_id, delta):
    """Changes user's reputation by delta (positive or negative). Returns new reputation."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO user_economy (user_id, reputation, coins) VALUES (?, 0, 1000)", (user_id,))
        cursor.execute("UPDATE user_economy SET reputation = reputation + ? WHERE user_id = ?", (delta, user_id))
        cursor.execute("SELECT reputation FROM user_economy WHERE user_id = ?", (user_id,))
        new_rep = cursor.fetchone()['reputation']
        conn.commit()
        conn.close()
        return new_rep

MAX_COINS = 9_000_000_000_000_000_000

def change_user_coins(user_id, delta):
    """Changes user's coins by delta. Returns new coins."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            delta = int(delta)
            if delta > MAX_COINS:
                delta = MAX_COINS
            elif delta < -MAX_COINS:
                delta = -MAX_COINS
            cursor.execute("INSERT OR IGNORE INTO user_economy (user_id, reputation, coins) VALUES (?, 0, 1000)", (user_id,))
            cursor.execute("UPDATE user_economy SET coins = MIN(?, MAX(0, coins + ?)) WHERE user_id = ?", (MAX_COINS, delta, user_id))
            cursor.execute("SELECT coins FROM user_economy WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            new_coins = row['coins'] if row else 1000
            conn.commit()
        except Exception as e:
            logger.error(f"change_user_coins error: {e}")
            new_coins = 1000
        finally:
            conn.close()
        return new_coins

def claim_daily_bonus(user_id, bonus_amount=1000, cooldown_hours=4):
    """Claims daily/periodic bonus for user. Returns (success, new_coins, amount_claimed, wait_seconds)."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO user_economy (user_id, reputation, coins) VALUES (?, 0, 1000)", (user_id,))
        cursor.execute("SELECT coins, last_daily FROM user_economy WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        current_coins = row['coins'] if row else 0
        last_daily_str = row['last_daily'] if row else None
        
        now = datetime.datetime.now()
        can_claim = False
        wait_sec = 0
        
        if not last_daily_str or current_coins == 0:
            can_claim = True
        else:
            try:
                last_dt = datetime.datetime.strptime(last_daily_str, "%Y-%m-%d %H:%M:%S")
                diff = (now - last_dt).total_seconds()
                req_diff = cooldown_hours * 3600
                if diff >= req_diff:
                    can_claim = True
                else:
                    wait_sec = int(req_diff - diff)
            except Exception:
                can_claim = True
                
        if can_claim:
            cursor.execute(
                "UPDATE user_economy SET coins = coins + ?, last_daily = ? WHERE user_id = ?",
                (bonus_amount, now.strftime("%Y-%m-%d %H:%M:%S"), user_id)
            )
            cursor.execute("SELECT coins FROM user_economy WHERE user_id = ?", (user_id,))
            new_coins = cursor.fetchone()['coins']
            conn.commit()
            conn.close()
            return True, new_coins, bonus_amount, 0
        else:
            conn.close()
            return False, current_coins, 0, wait_sec

def set_user_coins(user_id, coins_amount):
    """Sets exact coins amount for a user. Returns new coins."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            coins_amount = max(0, min(MAX_COINS, int(coins_amount)))
            cursor.execute("INSERT OR IGNORE INTO user_economy (user_id, reputation, coins) VALUES (?, 0, 1000)", (user_id,))
            cursor.execute("UPDATE user_economy SET coins = ? WHERE user_id = ?", (coins_amount, user_id))
            cursor.execute("SELECT coins FROM user_economy WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            new_coins = row['coins'] if row else coins_amount
            conn.commit()
        except Exception as e:
            logger.error(f"set_user_coins error: {e}")
            new_coins = coins_amount
        finally:
            conn.close()
        return new_coins

def set_user_rep(user_id, rep_amount):
    """Sets exact reputation amount for a user. Returns new reputation."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            rep_amount = max(-1000000, min(1000000, int(rep_amount)))
            cursor.execute("INSERT OR IGNORE INTO user_economy (user_id, reputation, coins) VALUES (?, 0, 1000)", (user_id,))
            cursor.execute("UPDATE user_economy SET reputation = ? WHERE user_id = ?", (rep_amount, user_id))
            cursor.execute("SELECT reputation FROM user_economy WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            new_rep = row['reputation'] if row else rep_amount
            conn.commit()
        except Exception as e:
            logger.error(f"set_user_rep error: {e}")
            new_rep = rep_amount
        finally:
            conn.close()
        return new_rep

WORK_JOBS = [
    ("👨‍💻 Написал высоконагруженный бэкенд на Python & FastAPI", 250, 450),
    ("⚡️ Настроил reverse proxy и ускорил Gemini 3.7 Pro", 300, 500),
    ("🛡 Нашел 0-day уязвимость и пропатчил PE-бинарник", 350, 600),
    ("🍕 Доставил энергетики и пиццу создателю k3rnel", 200, 400),
    ("🤖 Обучил нейросеть новым токсичным панчам", 280, 480),
    ("🎨 Сгенерировал 100 реалистичных Gemini Imagen 3 Pro артов", 220, 420),
    ("⛏ Помайнил криптовалюту на умном чайнике", 150, 350),
    ("💼 Оказал платную консультацию по архитектуре C++", 320, 550)
]

def claim_work_payout(user_id, cooldown_seconds=1800):
    """
    User works and earns coins with cooldown (default 30 mins).
    Returns (success, new_coins, earned_amount, wait_seconds, job_title)
    """
    import random
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO user_economy (user_id, reputation, coins) VALUES (?, 0, 1000)", (user_id,))
        cursor.execute("SELECT coins, last_work FROM user_economy WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        current_coins = row['coins'] if row else 0
        last_work_str = row['last_work'] if row else None
        
        now = datetime.datetime.now()
        can_work = False
        wait_sec = 0
        
        if not last_work_str:
            can_work = True
        else:
            try:
                last_work_dt = datetime.datetime.strptime(last_work_str, "%Y-%m-%d %H:%M:%S")
                diff = (now - last_work_dt).total_seconds()
                if diff >= cooldown_seconds:
                    can_work = True
                else:
                    wait_sec = int(cooldown_seconds - diff)
            except Exception:
                can_work = True
                
        if can_work:
            job_text, min_c, max_c = random.choice(WORK_JOBS)
            earned = random.randint(min_c, max_c)
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "UPDATE user_economy SET coins = coins + ?, last_work = ? WHERE user_id = ?",
                (earned, now_str, user_id)
            )
            cursor.execute("SELECT coins FROM user_economy WHERE user_id = ?", (user_id,))
            new_coins = cursor.fetchone()['coins']
            conn.commit()
            conn.close()
            return True, new_coins, earned, 0, job_text
        else:
            conn.close()
            return False, current_coins, 0, wait_sec, ""

def transfer_user_coins(from_uid, to_uid, amount):
    """
    Transfers coins from from_uid to to_uid with a 3% bank commission.
    Returns (success: bool, message: str, sender_new_coins: int, recipient_new_coins: int, fee: int)
    """
    if from_uid == to_uid:
        return False, "Нельзя переводить монеты самому себе!", 0, 0, 0
    if amount <= 0:
        return False, "Сумма перевода должна быть больше 0!", 0, 0, 0
    if amount > 1_000_000_000:
        return False, "Максимальная сумма одного перевода — 1,000,000,000 монет!", 0, 0, 0

    commission = max(1, int(amount * 0.03))
    received = amount - commission

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO user_economy (user_id, reputation, coins) VALUES (?, 0, 1000)", (from_uid,))
        cursor.execute("INSERT OR IGNORE INTO user_economy (user_id, reputation, coins) VALUES (?, 0, 1000)", (to_uid,))
        cursor.execute("SELECT coins FROM user_economy WHERE user_id = ?", (from_uid,))
        sender_coins = cursor.fetchone()['coins']
        if sender_coins < amount:
            conn.close()
            return False, f"Недостаточно монет для перевода! У вас 🪙 {sender_coins:,}, требуется 🪙 {amount:,}.", sender_coins, 0, 0

        cursor.execute("UPDATE user_economy SET coins = coins - ? WHERE user_id = ?", (amount, from_uid))
        cursor.execute("UPDATE user_economy SET coins = coins + ? WHERE user_id = ?", (received, to_uid))
        cursor.execute("SELECT coins FROM user_economy WHERE user_id = ?", (from_uid,))
        new_sender_coins = cursor.fetchone()['coins']
        cursor.execute("SELECT coins FROM user_economy WHERE user_id = ?", (to_uid,))
        new_recipient_coins = cursor.fetchone()['coins']
        conn.commit()
        conn.close()
        return True, "Перевод успешно выполнен!", new_sender_coins, new_recipient_coins, commission

SHOP_ITEMS = [
    {"id": "lucky_charm", "name": "🎲 Амулет Удачи в Казино", "price": 3000, "desc": "+15% к шансу выигрыша в /casino и /dice"},
    {"id": "rep_badge", "name": "🎖 Медаль Авторитета", "price": 5000, "desc": "+50 единиц уважения (репутации) профиля"},
    {"id": "hacker_badge", "name": "💻 Бейдж Кибер-Хакер", "price": 10000, "desc": "Особый статус Архитектора в профиле"},
    {"id": "vip_pass", "name": "⭐️ VIP Пропуск на 3 дня", "price": 25000, "desc": "3 дня полного Premium безлимита на фото и код"}
]

def get_shop_items():
    return SHOP_ITEMS

def buy_shop_item(user_id, item_id):
    """Buys an item from the shop using bot coins. Returns (success: bool, message: str, new_coins: int)"""
    item = next((i for i in SHOP_ITEMS if i["id"] == item_id), None)
    if not item:
        return False, "Предмет не найден в магазине.", 0

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO user_economy (user_id, reputation, coins) VALUES (?, 0, 1000)", (user_id,))
        cursor.execute("SELECT coins, reputation, inventory FROM user_economy WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        coins = row['coins'] if row else 0
        rep = row['reputation'] if row else 0
        inv_str = row['inventory'] if row and 'inventory' in row.keys() and row['inventory'] else "[]"
        try:
            inv = json.loads(inv_str)
        except Exception:
            inv = []

        if coins < item["price"]:
            conn.close()
            return False, f"Недостаточно монет! Требуется 🪙 {item['price']:,}, а у вас 🪙 {coins:,}.", coins

        new_coins = coins - item["price"]
        inv.append(item["id"])
        
        # Apply instant item effects
        if item["id"] == "rep_badge":
            cursor.execute("UPDATE user_economy SET coins = ?, reputation = reputation + 50, inventory = ? WHERE user_id = ?", (new_coins, json.dumps(inv), user_id))
        elif item["id"] == "vip_pass":
            cursor.execute("UPDATE user_economy SET coins = ?, inventory = ? WHERE user_id = ?", (new_coins, json.dumps(inv), user_id))
            set_user_premium(user_id, days=3, stars_paid=0)
        else:
            cursor.execute("UPDATE user_economy SET coins = ?, inventory = ? WHERE user_id = ?", (new_coins, json.dumps(inv), user_id))

        conn.commit()
        conn.close()
        return True, f"Вы успешно приобрели «{item['name']}» за 🪙 {item['price']:,} монет!", new_coins

from collections import OrderedDict
import hashlib

class FastMemoryCache:
    """Thread-safe LRU In-Memory Cache with TTL expiration and hit/miss analytics."""
    def __init__(self, max_size=2000, default_ttl=300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key):
        with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None
            val, exp = self._cache[key]
            if exp and time.time() > exp:
                del self._cache[key]
                self.misses += 1
                return None
            self._cache.move_to_end(key)
            self.hits += 1
            return val

    def set(self, key, value, ttl=None):
        with self._lock:
            exp = time.time() + (ttl if ttl is not None else self.default_ttl) if (ttl is not None or self.default_ttl) else None
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, exp)
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def delete(self, key):
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self):
        with self._lock:
            self._cache.clear()

    def get_stats(self):
        with self._lock:
            total = self.hits + self.misses
            ratio = (self.hits / total * 100) if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio_percent": round(ratio, 2)
            }

# Global in-memory LRU caches for sub-millisecond data retrieval
user_modes_cache = FastMemoryCache(max_size=5000, default_ttl=600)
topic_modes_cache = FastMemoryCache(max_size=3000, default_ttl=600)
topic_automod_cache = FastMemoryCache(max_size=3000, default_ttl=600)
user_voices_cache = FastMemoryCache(max_size=5000, default_ttl=600)
user_premium_cache = FastMemoryCache(max_size=5000, default_ttl=300)
chat_ai_engines_cache = FastMemoryCache(max_size=5000, default_ttl=600)
app_settings_cache = FastMemoryCache(max_size=500, default_ttl=1800)
response_cache = FastMemoryCache(max_size=2000, default_ttl=300)
search_cache = FastMemoryCache(max_size=1000, default_ttl=1800)
user_blocked_cache = FastMemoryCache(max_size=5000, default_ttl=600)

def record_error_experience(error_type, error_msg, traceback_str="", context=""):
    """
    Autonomous learning & error diagnosis:
    Logs runtime errors, diagnoses root cause, and stores in SQLite knowledge base.
    """
    sig_raw = f"{error_type}:{str(error_msg)[:120]}"
    error_signature = hashlib.md5(sig_raw.encode('utf-8', errors='ignore')).hexdigest()[:16]
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Autonomous root cause diagnosis
    root_cause = "Неизвестный сбой выполнения"
    solution = "Повтор запроса или переход на резервный обработчик"
    lowered = f"{error_type} {error_msg}".lower()

    if "429" in lowered or "quota" in lowered or "resourceexhausted" in lowered:
        root_cause = "Исчерпан лимит квот модели Gemini"
        solution = "Автоматический переход на следующую модель из списка GEMINI_MODELS"
    elif "timeout" in lowered or "timed out" in lowered:
        root_cause = "Таймаут сетевого соединения"
        solution = "Увеличение таймаута и использование постоянного пула соединений Keep-Alive"
    elif "json" in lowered or "decode" in lowered:
        root_cause = "Невалидный формат JSON ответа"
        solution = "Очистка невалидных символов и безопасный fallback"
    elif "unicode" in lowered or "charmap" in lowered or "utf-8" in lowered:
        root_cause = "Ошибка кодировки символов"
        solution = "Принудительная переконфигурация UTF-8 потока sys.stdout/sys.stderr"
    elif "duplicate" in lowered or "unique" in lowered:
        root_cause = "Попытка повторной записи уникального ключа"
        solution = "Использование конструкции ON CONFLICT DO UPDATE"

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO learning_experience (
                    error_signature, error_type, error_message, traceback_snippet,
                    context_data, root_cause, solution, occurrence_count, first_seen, last_seen, resolved
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 1)
                ON CONFLICT(error_signature) DO UPDATE SET
                    occurrence_count = occurrence_count + 1,
                    last_seen = excluded.last_seen,
                    traceback_snippet = excluded.traceback_snippet,
                    context_data = excluded.context_data
            ''', (error_signature, str(error_type), str(error_msg)[:300], str(traceback_str)[:600], str(context)[:300], root_cause, solution, now_str, now_str))
            conn.commit()
        except Exception as e:
            logger.error(f"Error recording learning experience: {e}")
        finally:
            conn.close()
    return error_signature

def get_learning_stats():
    """Returns summary of learned errors and experience database."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) as total_errors, SUM(occurrence_count) as total_occurrences FROM learning_experience")
            row = cursor.fetchone()
            cursor.execute("SELECT error_type, root_cause, solution, occurrence_count, last_seen FROM learning_experience ORDER BY last_seen DESC LIMIT 10")
            recent = [dict(r) for r in cursor.fetchall()]
            return {
                "total_unique_errors": row["total_errors"] if row else 0,
                "total_occurrences": row["total_occurrences"] if (row and row["total_occurrences"]) else 0,
                "recent_learned_fixes": recent
            }
        except Exception as e:
            logger.error(f"Error getting learning stats: {e}")
            return {"total_unique_errors": 0, "total_occurrences": 0, "recent_learned_fixes": []}
        finally:
            conn.close()

def get_user_mode(user_id):
    """Retrieves current AI personality mode for user (defaults to 'evil' for creator, 'default' for others) with high-speed LRU memory caching."""
    if not user_id:
        return "default"
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return "default"
        
    cached = user_modes_cache.get(uid)
    if cached is not None:
        return cached
        
    CREATOR_IDS = (6363403785, 7758799391)
    default_mode = "evil" if uid in CREATOR_IDS else "default"
    mode = default_mode
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT mode FROM user_settings WHERE user_id = ?", (uid,))
            row = cursor.fetchone()
            if row and row["mode"]:
                mode = str(row["mode"])
            elif uid in CREATOR_IDS:
                # Force ensure creator is evil in DB
                cursor.execute("INSERT OR REPLACE INTO user_settings (user_id, mode) VALUES (?, 'evil')", (uid,))
                conn.commit()
                mode = "evil"
        except Exception as e:
            logger.error(f"Error in get_user_mode: {e}")
        finally:
            conn.close()

    user_modes_cache.set(uid, mode)
    return mode

def set_user_mode(user_id, mode):
    """Sets AI personality mode for user in both memory cache and SQLite."""
    if not user_id:
        return False
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return False
        
    mode_str = str(mode)
    user_modes_cache.set(uid, mode_str)
    
    success = False
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO user_settings (user_id, mode)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET mode = excluded.mode
            ''', (uid, mode_str))
            conn.commit()
            success = True
        except Exception as e:
            logger.error(f"Error in set_user_mode: {e}")
            success = False
        finally:
            conn.close()
            
    if success:
        try:
            clear_user_history(uid)
        except Exception:
            pass
            
    return success

# ==========================================
# FORUM TOPICS (PER-TOPIC MODES & AUTOMOD)
# ==========================================

def get_topic_mode(chat_id, thread_id=None):
    """
    Retrieves AI personality mode for a specific forum topic/thread.
    If topic mode is not configured, falls back to group mode (get_user_mode).
    """
    if thread_id is None:
        return get_user_mode(chat_id)
        
    try:
        cid = int(chat_id)
        tid = int(thread_id)
    except (ValueError, TypeError):
        return get_user_mode(chat_id)

    cache_k = f"{cid}:{tid}"
    cached = topic_modes_cache.get(cache_k)
    if cached is not None:
        return cached

    topic_mode = None
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT mode FROM chat_topics WHERE chat_id = ? AND thread_id = ?", (cid, tid))
            row = cursor.fetchone()
            if row and row["mode"]:
                topic_mode = str(row["mode"])
        except Exception as e:
            logger.error(f"Error in get_topic_mode: {e}")
        finally:
            conn.close()

    res = topic_mode or get_user_mode(cid)
    topic_modes_cache.set(cache_k, res)
    return res

def set_topic_mode(chat_id, thread_id, mode):
    """
    Sets AI personality mode for a specific forum topic/thread.
    """
    if thread_id is None:
        return set_user_mode(chat_id, mode)

    try:
        cid = int(chat_id)
        tid = int(thread_id)
    except (ValueError, TypeError):
        return set_user_mode(chat_id, mode)

    mode_str = str(mode)
    cache_k = f"{cid}:{tid}"
    topic_modes_cache.set(cache_k, mode_str)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    success = False
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO chat_topics (chat_id, thread_id, mode, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id, thread_id) DO UPDATE SET mode = excluded.mode, updated_at = excluded.updated_at
            ''', (cid, tid, mode_str, now))
            conn.commit()
            success = True
        except Exception as e:
            logger.error(f"Error in set_topic_mode: {e}")
        finally:
            conn.close()

    return success

def is_topic_automod_enabled(chat_id, thread_id=None):
    """
    Checks if automoderation is active in this specific forum topic.
    Allows creating free-speech / roasting / bullying / flood topics without bot interference.
    """
    if thread_id is None:
        return True

    try:
        cid = int(chat_id)
        tid = int(thread_id)
    except (ValueError, TypeError):
        return True

    cache_k = f"am:{cid}:{tid}"
    cached = topic_automod_cache.get(cache_k)
    if cached is not None:
        return cached

    enabled = True
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT automod_enabled FROM chat_topics WHERE chat_id = ? AND thread_id = ?", (cid, tid))
            row = cursor.fetchone()
            if row and row["automod_enabled"] is not None:
                enabled = bool(row["automod_enabled"])
        except Exception as e:
            logger.error(f"Error in is_topic_automod_enabled: {e}")
        finally:
            conn.close()

    topic_automod_cache.set(cache_k, enabled)
    return enabled

def set_topic_automod_enabled(chat_id, thread_id, enabled):
    """
    Enables or disables automoderation for a specific forum topic.
    """
    int_val = 1 if enabled else 0
    if thread_id is None:
        # Global fallback for chat
        set_chat_automod_setting(chat_id, "action", "warn" if enabled else "none")
        return True

    try:
        cid = int(chat_id)
        tid = int(thread_id)
    except (ValueError, TypeError):
        return False

    cache_k = f"am:{cid}:{tid}"
    topic_automod_cache.set(cache_k, bool(enabled))

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO chat_topics (chat_id, thread_id, automod_enabled, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id, thread_id) DO UPDATE SET automod_enabled = excluded.automod_enabled, updated_at = excluded.updated_at
            ''', (cid, tid, int_val, now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error in set_topic_automod_enabled: {e}")
            return False
        finally:
            conn.close()

def get_topic_automod_settings(chat_id, thread_id=None):
    """
    Returns effective automod settings for a forum topic.
    Inherits chat automod settings as baseline, overlays topic-specific overrides.
    """
    base_settings = get_chat_automod_settings(chat_id)
    if thread_id is None:
        return base_settings

    try:
        cid = int(chat_id)
        tid = int(thread_id)
    except (ValueError, TypeError):
        return base_settings

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM chat_topics WHERE chat_id = ? AND thread_id = ?", (cid, tid))
            row = cursor.fetchone()
            if row:
                merged = dict(base_settings)
                col_keys = row.keys()
                if "automod_enabled" in col_keys and row["automod_enabled"] is not None:
                    merged["automod_enabled"] = int(row["automod_enabled"])
                    if merged["automod_enabled"] == 0:
                        merged["action"] = "none"
                for k in base_settings.keys():
                    if k in col_keys and row[k] is not None:
                        val = row[k]
                        if isinstance(base_settings[k], int):
                            try:
                                merged[k] = int(val)
                            except:
                                pass
                        else:
                            merged[k] = str(val)
                return merged
        except Exception as e:
            logger.error(f"Error in get_topic_automod_settings: {e}")
        finally:
            conn.close()

    return base_settings

def set_topic_automod_setting(chat_id, thread_id, key, value):
    """
    Sets a specific automod override setting for a forum topic.
    """
    if thread_id is None:
        return set_chat_automod_setting(chat_id, key, value)

    try:
        cid = int(chat_id)
        tid = int(thread_id)
    except (ValueError, TypeError):
        return False

    valid_cols = [
        "anti_mat", "anti_18plus", "anti_nsfw_media", "anti_links",
        "anti_ai", "anti_channels", "anti_anonymous", "exempt_admins", "action", "warn_limit",
        "warn_punishment", "punishment_duration", "automod_enabled"
    ]
    if key not in valid_cols:
        return False

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO chat_topics (chat_id, thread_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id, thread_id) DO NOTHING
            ''', (cid, tid, now))
            cursor.execute(f"UPDATE chat_topics SET {key} = ?, updated_at = ? WHERE chat_id = ? AND thread_id = ?", (value, now, cid, tid))
            conn.commit()
            if key == "automod_enabled":
                topic_automod_cache.set(f"am:{cid}:{tid}", bool(value))
            return True
        except Exception as e:
            logger.error(f"Error in set_topic_automod_setting ({key}={value}): {e}")
            return False
        finally:
            conn.close()

def get_topic_info(chat_id, thread_id):
    """Retrieves all topic settings from chat_topics."""
    try:
        cid = int(chat_id)
        tid = int(thread_id)
    except (ValueError, TypeError):
        return {}

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM chat_topics WHERE chat_id = ? AND thread_id = ?", (cid, tid))
            row = cursor.fetchone()
            return dict(row) if row else {}
        except Exception as e:
            logger.error(f"Error in get_topic_info: {e}")
            return {}
        finally:
            conn.close()

def get_topic_rules(chat_id, thread_id=None):
    """Retrieves rules for a specific forum topic, or None if not set (fallback to group rules)."""
    if not thread_id:
        return None
    try:
        cid = int(chat_id)
        tid = int(thread_id)
    except (ValueError, TypeError):
        return None

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT rules FROM chat_topics WHERE chat_id = ? AND thread_id = ?", (cid, tid))
            row = cursor.fetchone()
            if row and row["rules"] and str(row["rules"]).strip():
                return str(row["rules"]).strip()
            return None
        except Exception as e:
            logger.error(f"Error in get_topic_rules: {e}")
            return None
        finally:
            conn.close()

def set_topic_rules(chat_id, thread_id, rules_text):
    """Sets custom rules for a specific forum topic."""
    if not thread_id:
        return False
    try:
        cid = int(chat_id)
        tid = int(thread_id)
    except (ValueError, TypeError):
        return False

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO chat_topics (chat_id, thread_id, rules, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id, thread_id) DO UPDATE SET
                    rules = excluded.rules,
                    updated_at = excluded.updated_at
            ''', (cid, tid, rules_text, now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error in set_topic_rules: {e}")
            return False
        finally:
            conn.close()

def is_user_blocked(user_id) -> bool:
    """Checks if a user is blocked in the bot (never blocks Creator)."""
    if not user_id:
        return False
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return False

    CREATOR_IDS = (6363403785, 7758799391)
    if uid in CREATOR_IDS:
        return False

    cached = user_blocked_cache.get(uid)
    if cached is not None:
        return bool(cached)

    blocked = False
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM blocked_users WHERE user_id = ?", (uid,))
            blocked = cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error in is_user_blocked: {e}")
        finally:
            conn.close()

    user_blocked_cache.set(uid, blocked)
    return blocked

def set_user_blocked(user_id, blocked: bool = True, reason: str = "") -> bool:
    """Sets user blocked state in SQLite and cache (Creator can never be blocked)."""
    if not user_id:
        return False
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return False

    CREATOR_IDS = (6363403785, 7758799391)
    if uid in CREATOR_IDS:
        return False

    user_blocked_cache.set(uid, bool(blocked))
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            if blocked:
                cursor.execute('''
                    INSERT OR REPLACE INTO blocked_users (user_id, blocked_at, reason)
                    VALUES (?, ?, ?)
                ''', (uid, now, reason or "Заблокирован администратором"))
            else:
                cursor.execute("DELETE FROM blocked_users WHERE user_id = ?", (uid,))
            conn.commit()
        except Exception as e:
            logger.error(f"Error in set_user_blocked: {e}")
            return False
        finally:
            conn.close()

    save_persistent_backup(force=True)
    return True

def get_chat(chat_id):
    """Retrieves chat metadata by chat_id."""
    if not chat_id:
        return None
    try:
        cid = int(chat_id)
    except (ValueError, TypeError):
        return None
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT chat_id, chat_title, chat_type, message_count, created_at, last_activity FROM chats WHERE chat_id = ?', (cid,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting chat {chat_id}: {e}")
            return None
        finally:
            conn.close()

def delete_chat(chat_id) -> bool:
    """Deletes a chat and its messages from database when the bot leaves a group."""
    if not chat_id:
        return False
    try:
        cid = int(chat_id)
    except (ValueError, TypeError):
        return False

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            for tbl in ["chats", "messages", "business_chats", "chat_sniffer_settings", "chat_automod_settings", "secretary_chat_status", "secretary_chat_modes"]:
                try:
                    cursor.execute(f"DELETE FROM {tbl} WHERE chat_id = ?", (cid,))
                except Exception:
                    pass
            conn.commit()
        except Exception as e:
            logger.error(f"Error in delete_chat: {e}")
            return False
        finally:
            conn.close()

    save_persistent_backup(force=True)
    return True

def get_chat_ai_engine(chat_id):
    """Retrieves current AI engine for chat or user ('gemini', 'deepseek', 'glm'). Defaults to 'gemini' (AI FOR COPIL)."""
    if not chat_id:
        return "gemini"
    cid = str(chat_id)
    cached = chat_ai_engines_cache.get(cid)
    if cached is not None:
        return cached
    key = f"ai_engine_{cid}"
    val = get_app_setting(key, "gemini")
    chat_ai_engines_cache.set(cid, val)
    return val

def set_chat_ai_engine(chat_id, engine):
    """Sets AI engine for chat or user ('gemini', 'deepseek', 'glm')."""
    if not chat_id:
        return False
    cid = str(chat_id)
    val = engine if engine in ["gemini", "banmax", "deepseek", "glm"] else "gemini"
    chat_ai_engines_cache.set(cid, val)
    key = f"ai_engine_{cid}"
    res = set_app_setting(key, val)
    try:
        save_persistent_backup(force=True)
    except Exception:
        pass
    return res

def get_user_voice(user_id):
    """Retrieves current preferred voice style for user ('default', 'anime', 'girl', 'man') with caching."""
    if not user_id:
        return "default"
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return "default"

    cached = user_voices_cache.get(uid)
    if cached is not None:
        return cached

    voice = "default"
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT voice_style FROM user_settings WHERE user_id = ?", (uid,))
            row = cursor.fetchone()
            if row and row["voice_style"]:
                voice = str(row["voice_style"])
        except Exception as e:
            logger.error(f"Error in get_user_voice: {e}")
        finally:
            conn.close()

    user_voices_cache.set(uid, voice)
    return voice

def set_user_voice(user_id, voice_style):
    """Sets preferred voice style for user in both cache and SQLite."""
    if not user_id:
        return False
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return False

    v_str = str(voice_style).strip().lower()
    user_voices_cache.set(uid, v_str)

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO user_settings (user_id, voice_style)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET voice_style = excluded.voice_style
            ''', (uid, v_str))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error in set_user_voice: {e}")
            return False
        finally:
            conn.close()

# ==========================================
# TELEGRAM STARS & PREMIUM SUBSCRIPTIONS
# ==========================================

CREATOR_ID = 6363403785
FREE_LIMIT_PHOTOS = 3
FREE_LIMIT_QUERIES = 90
FREE_LIMIT_DOCS = 99999999

def is_user_premium(user_id):
    """Checks if the user has an active Premium subscription or is Creator with fast LRU caching."""
    if not user_id:
        return False
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return False

    if uid == CREATOR_ID:
        return True

    cached = user_premium_cache.get(uid)
    if cached is not None:
        return cached

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_prem = False
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT is_premium, expires_at FROM user_subscriptions
                WHERE user_id = ?
            ''', (uid,))
            row = cursor.fetchone()
            if row and row["is_premium"] == 1:
                exp = row["expires_at"]
                if exp in ["Бесконечно", "бесконечно", "Навсегда", "навсегда", "infinite", "Forever", "вечно", "∞"]:
                    is_prem = True
                elif exp and exp > now_str:
                    is_prem = True
        except Exception as e:
            logger.error(f"Error checking is_user_premium: {e}")
        finally:
            conn.close()

    user_premium_cache.set(uid, is_prem)
    return is_prem

def is_user_premium_cached(user_id):
    """Direct alias for is_user_premium with instant in-memory lookup."""
    return is_user_premium(user_id)

def set_user_premium(user_id, days=30, stars_paid=59):
    """Activates or extends Premium subscription for user."""
    if not user_id:
        return False
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return False

    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    is_infinite = False
    if str(days).lower() in ["infinite", "бесконечно", "навсегда", "forever", "inf", "вечно", "∞", "-1"]:
        is_infinite = True
    elif isinstance(days, (int, float)) and days >= 9000:
        is_infinite = True

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            if is_infinite:
                new_exp_str = "Бесконечно"
            else:
                num_days = int(days) if str(days).isdigit() else 30
                cursor.execute("SELECT expires_at FROM user_subscriptions WHERE user_id = ?", (uid,))
                row = cursor.fetchone()
                if row and row["expires_at"]:
                    try:
                        if row["expires_at"] in ["Бесконечно", "бесконечно", "Навсегда", "навсегда", "infinite"]:
                            new_exp = now + datetime.timedelta(days=num_days)
                        else:
                            current_exp = datetime.datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
                            if current_exp > now:
                                new_exp = current_exp + datetime.timedelta(days=num_days)
                            else:
                                new_exp = now + datetime.timedelta(days=num_days)
                    except Exception:
                        new_exp = now + datetime.timedelta(days=num_days)
                else:
                    new_exp = now + datetime.timedelta(days=num_days)

                new_exp_str = new_exp.strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute('''
                INSERT INTO user_subscriptions (user_id, is_premium, expires_at, stars_paid, updated_at)
                VALUES (?, 1, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    is_premium = 1,
                    expires_at = excluded.expires_at,
                    stars_paid = stars_paid + excluded.stars_paid,
                    updated_at = excluded.updated_at
            ''', (uid, new_exp_str, stars_paid, now_str))
            conn.commit()
            user_premium_cache.set(uid, True)
            return True, new_exp_str
        except Exception as e:
            logger.error(f"Error setting user premium: {e}")
            return False, None
        finally:
            conn.close()

def get_user_subscription(user_id):
    """Returns detailed subscription info for user."""
    if not user_id:
        return {"is_premium": False, "status": "Free", "expires_at": None, "days_left": 0}
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return {"is_premium": False, "status": "Free", "expires_at": None, "days_left": 0}

    if uid == CREATOR_ID:
        return {"is_premium": True, "status": "👑 Creator (Вечный Безлимит)", "expires_at": "Навсегда", "days_left": 9999}

    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT is_premium, expires_at, stars_paid FROM user_subscriptions WHERE user_id = ?", (uid,))
            row = cursor.fetchone()
            if row and row["is_premium"] == 1 and row["expires_at"]:
                exp = row["expires_at"]
                if exp in ["Бесконечно", "бесконечно", "Навсегда", "навсегда", "infinite", "Forever", "вечно", "∞"]:
                    return {
                        "is_premium": True,
                        "status": "⭐️ Premium (Бесконечно)",
                        "expires_at": "Бесконечно",
                        "days_left": "Бесконечно",
                        "stars_paid": row["stars_paid"]
                    }
                elif exp > now_str:
                    try:
                        exp_dt = datetime.datetime.strptime(exp, "%Y-%m-%d %H:%M:%S")
                        days_left = max(1, (exp_dt - now).days + 1)
                    except Exception:
                        days_left = 30
                    return {
                        "is_premium": True,
                        "status": "⭐️ Premium",
                        "expires_at": exp,
                        "days_left": days_left,
                        "stars_paid": row["stars_paid"]
                    }
        except Exception as e:
            logger.error(f"Error getting subscription: {e}")
        finally:
            conn.close()

    return {"is_premium": False, "status": "Free", "expires_at": None, "days_left": 0}

def check_and_increment_daily_limit(user_id, limit_type='query'):
    """
    Checks daily usage for free users (3 photos/day, 90 code queries/5h).
    Premium users get unlimited access.
    Returns: (allowed: bool, current_count: int, max_limit: int)
    """
    if not user_id:
        return True, 0, -1

    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return True, 0, -1

    if is_user_premium(uid):
        return True, 0, -1

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    max_limit = FREE_LIMIT_PHOTOS if limit_type == 'photo' else (FREE_LIMIT_DOCS if limit_type == 'doc' else FREE_LIMIT_QUERIES)
    col_name = "photos_count" if limit_type == 'photo' else ("docs_count" if limit_type == 'doc' else "queries_count")

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT {col_name} FROM daily_usage WHERE user_id = ? AND date_str = ?", (uid, date_str))
            row = cursor.fetchone()
            current_val = row[col_name] if row else 0

            if current_val >= max_limit:
                return False, current_val, max_limit

            # Increment count
            cursor.execute(f'''
                INSERT INTO daily_usage (user_id, date_str, {col_name})
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, date_str) DO UPDATE SET {col_name} = {col_name} + 1
            ''', (uid, date_str))
            conn.commit()
            return True, current_val + 1, max_limit
        except Exception as e:
            logger.error(f"Error checking daily limit: {e}")
            return True, 0, max_limit
        finally:
            conn.close()

def get_daily_usage(user_id):
    """Returns today's usage dict for a user."""
    if not user_id:
        return {"photos": 0, "queries": 0, "docs": 0}
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return {"photos": 0, "queries": 0, "docs": 0}

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT photos_count, queries_count, docs_count FROM daily_usage WHERE user_id = ? AND date_str = ?", (uid, date_str))
            row = cursor.fetchone()
            if row:
                return {
                    "photos": row["photos_count"] or 0,
                    "queries": row["queries_count"] or 0,
                    "docs": row["docs_count"] or 0
                }
        except Exception as e:
            logger.error(f"Error getting daily usage: {e}")
        finally:
            conn.close()

    return {"photos": 0, "queries": 0, "docs": 0}

def save_script(script_id, title, language, code, author_id=None, author_name=None):
    """Saves a script into the database for raw cloud hosting and sharing."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO scripts (script_id, title, language, code, author_id, author_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (script_id, title, language, code, author_id, author_name, now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving script {script_id}: {e}")
            return False
        finally:
            conn.close()

def get_script(script_id):
    """Retrieves script data by script_id, supporting exact, suffix and fuzzy slug matching."""
    if not script_id:
        return None
    clean_id = script_id.strip()
    for ext in ['.lua', '.luau', '.cpp', '.py', '.js', '.txt', '.html', '.htm', '.json']:
        if clean_id.endswith(ext):
            clean_id = clean_id[:-len(ext)]
            break

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # 1. Exact match
            cursor.execute("SELECT * FROM scripts WHERE script_id = ? OR script_id = ?", (script_id.strip(), clean_id))
            row = cursor.fetchone()
            if row:
                return dict(row)
            
            # 2. Suffix match (e.g. timestamp suffix _8779)
            if "_" in clean_id:
                suffix = clean_id.rsplit("_", 1)[-1]
                if len(suffix) >= 4:
                    cursor.execute("SELECT * FROM scripts WHERE script_id LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%_{suffix}",))
                    row = cursor.fetchone()
                    if row:
                        return dict(row)
            
            # 3. Prefix/Substring match
            cursor.execute("SELECT * FROM scripts WHERE script_id LIKE ? OR title LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%{clean_id[:20]}%", f"%{clean_id[:20]}%"))
            row = cursor.fetchone()
            if row:
                return dict(row)
        except Exception as e:
            logger.error(f"Error getting script {script_id}: {e}")
        finally:
            conn.close()
    return None

def increment_script_views(script_id):
    """Increments script view count."""
    clean_id = script_id.strip()
    if clean_id.endswith('.lua') or clean_id.endswith('.cpp') or clean_id.endswith('.py') or clean_id.endswith('.js') or clean_id.endswith('.txt') or clean_id.endswith('.html'):
        clean_id = clean_id.rsplit('.', 1)[0]
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE scripts SET views = views + 1 WHERE script_id = ? OR script_id = ?", (script_id, clean_id))
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

def get_recent_scripts(limit=25):
    """Gets list of recently created/uploaded scripts."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT script_id, title, language, length(code) as code_size, author_name, views, created_at FROM scripts ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error getting recent scripts: {e}")
            return []
        finally:
            conn.close()

def get_latest_user_script(author_id=None):
    """Gets the most recently created script by author_id or globally."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            if author_id:
                cursor.execute("SELECT * FROM scripts WHERE author_id = ? ORDER BY created_at DESC LIMIT 1", (author_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
            cursor.execute("SELECT * FROM scripts ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
        except Exception as e:
            logger.error(f"Error getting latest user script: {e}")
        finally:
            conn.close()
def set_app_setting(key, value):
    """Sets a persistent global app setting (e.g. GITHUB_TOKEN)."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ok = False
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            ''', (str(key), str(value), now))
            conn.commit()
            ok = True
        except Exception as e:
            logger.error(f"Error saving app setting {key}: {e}")
            ok = False
        finally:
            conn.close()
    if ok:
        try:
            save_persistent_backup(force=True)
        except Exception:
            pass
    return ok

def get_app_setting(key, default=None):
    """Retrieves a persistent global app setting."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT value FROM app_settings WHERE key = ?", (str(key),))
            row = cursor.fetchone()
            if row and row["value"] is not None:
                return row["value"]
        except Exception as e:
            logger.error(f"Error getting app setting {key}: {e}")
        finally:
            conn.close()
    return default

def get_chat_automod_settings(chat_id):
    """Returns dictionary of automod filter settings for chat_id."""
    default_settings = {
        "anti_mat": 1,
        "anti_18plus": 1,
        "anti_nsfw_media": 1,
        "anti_links": 0,
        "anti_ai": 1,
        "anti_channels": 0,
        "anti_anonymous": 0,
        "exempt_admins": 0,
        "action": "warn",
        "warn_limit": 3,
        "warn_punishment": "mute",
        "punishment_duration": "30m"
    }
    if not chat_id:
        return default_settings
        
    try:
        cid = int(chat_id)
    except (ValueError, TypeError):
        return default_settings
        
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM chat_automod WHERE chat_id = ?", (cid,))
            row = cursor.fetchone()
            if row:
                res = dict(default_settings)
                col_keys = row.keys()
                for k in default_settings.keys():
                    if k in col_keys and row[k] is not None:
                        val = row[k]
                        if isinstance(default_settings[k], int):
                            try:
                                res[k] = int(val)
                            except:
                                pass
                        else:
                            res[k] = str(val)
                return res
            else:
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT OR IGNORE INTO chat_automod "
                    "(chat_id, anti_mat, anti_18plus, anti_nsfw_media, anti_links, anti_ai, exempt_admins, action, warn_limit, warn_punishment, punishment_duration, updated_at) "
                    "VALUES (?, 1, 1, 1, 0, 1, 0, 'warn', 3, 'mute', '30m', ?)",
                    (cid, now)
                )
                conn.commit()
                return default_settings
        except Exception as e:
            logger.error(f"Error in get_chat_automod_settings: {e}")
            return default_settings
        finally:
            conn.close()

def set_chat_automod_setting(chat_id, key, value):
    """Sets a specific automod setting for chat_id."""
    if not chat_id:
        return False
    try:
        cid = int(chat_id)
    except (ValueError, TypeError):
        return False
        
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    valid_cols = [
        "anti_mat", "anti_18plus", "anti_nsfw_media", "anti_links",
        "anti_ai", "anti_channels", "anti_anonymous", "exempt_admins", "action", "warn_limit",
        "warn_punishment", "punishment_duration"
    ]
    if key not in valid_cols:
        return False
        
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO chat_automod (chat_id, updated_at) VALUES (?, ?)", (cid, now))
            cursor.execute(f"UPDATE chat_automod SET {key} = ?, updated_at = ? WHERE chat_id = ?", (value, now, cid))
            conn.commit()
            try:
                save_persistent_backup(force=False)
            except Exception:
                pass
            try:
                import db_sync
                db_sync.trigger_fast_sync(delay_sec=3.0)
            except Exception:
                pass
            return True
        except Exception as e:
            logger.error(f"Error updating automod setting {key}: {e}")
            return False
        finally:
            conn.close()

def save_chat_moderation_config(chat_id, config_dict):
    """Saves chat moderation config (rules, custom roles, warns, moders) into SQLite."""
    if not chat_id or not isinstance(config_dict, dict):
        return False
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cid_str = str(chat_id)
    raw_json = json.dumps(config_dict, ensure_ascii=False)
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_moderation_config (
                    chat_id TEXT PRIMARY KEY,
                    config_json TEXT,
                    updated_at TEXT
                )
            ''')
            cursor.execute('''
                INSERT INTO chat_moderation_config (chat_id, config_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET config_json = excluded.config_json, updated_at = excluded.updated_at
            ''', (cid_str, raw_json, now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving chat moderation config for {chat_id}: {e}")
            return False
        finally:
            conn.close()

def get_chat_moderation_config(chat_id):
    """Returns a single chat moderation config dict from SQLite or None."""
    if not chat_id:
        return None
    cid_str = str(chat_id)
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_moderation_config (
                    chat_id TEXT PRIMARY KEY,
                    config_json TEXT,
                    updated_at TEXT
                )
            ''')
            cursor.execute('SELECT config_json FROM chat_moderation_config WHERE chat_id = ?', (cid_str,))
            row = cursor.fetchone()
            if row and row["config_json"]:
                return json.loads(row["config_json"])
        except Exception as e:
            logger.error(f"Error getting chat moderation config for {chat_id}: {e}")
        finally:
            conn.close()
    return None

def get_all_chat_moderation_configs():
    """Returns a dictionary {chat_id_str: config_dict} from SQLite."""
    res = {}
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_moderation_config (
                    chat_id TEXT PRIMARY KEY,
                    config_json TEXT,
                    updated_at TEXT
                )
            ''')
            cursor.execute('SELECT chat_id, config_json FROM chat_moderation_config')
            for row in cursor.fetchall():
                try:
                    res[str(row["chat_id"])] = json.loads(row["config_json"])
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Error loading all chat moderation configs from SQLite: {e}")
        finally:
            conn.close()
    return res

# ==========================================
# BOT ADMIN PRIVILEGES & MESSAGE UTILITIES
# ==========================================

def add_bot_admin(user_id, username="", first_name="", granted_by=None):
    """Adds a user to bot administrators table."""
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return False
    ok = False
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO bot_admins (user_id, username, first_name, granted_by, granted_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (uid, username or "", first_name or "", granted_by, now))
            conn.commit()
            ok = True
        except Exception as e:
            logger.error(f"Error adding bot admin {uid}: {e}")
            ok = False
        finally:
            conn.close()
    if ok:
        try:
            save_persistent_backup(force=True)
        except Exception:
            pass
    return ok

def remove_bot_admin(user_id):
    """Removes a user from bot administrators."""
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return False
    ok = False
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM bot_admins WHERE user_id = ?', (uid,))
            conn.commit()
            ok = cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing bot admin {uid}: {e}")
            ok = False
        finally:
            conn.close()
    if ok:
        try:
            save_persistent_backup(force=True)
        except Exception:
            pass
    return ok

def is_bot_admin(user_id):
    """Checks if a user has bot administrator privileges (Creator k3rnel or registered in bot_admins)."""
    if not user_id:
        return False
    try:
        uid = int(getattr(user_id, 'id', user_id))
    except (ValueError, TypeError):
        return False
    if uid == 6363403785:  # Creator k3rnel
        return True
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT user_id FROM bot_admins WHERE user_id = ?', (uid,))
            row = cursor.fetchone()
            return bool(row)
        except Exception as e:
            logger.error(f"Error checking bot admin for {uid}: {e}")
            return False
        finally:
            conn.close()

def get_all_bot_admins():
    """Returns list of all active bot administrators."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT user_id, username, first_name, granted_by, granted_at FROM bot_admins ORDER BY granted_at DESC')
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error fetching bot admins: {e}")
            return []
        finally:
            conn.close()

def delete_message_by_id(message_id):
    """Deletes a specific message record by SQLite ID."""
    try:
        mid = int(message_id)
    except (ValueError, TypeError):
        return False
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM messages WHERE id = ?', (mid,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting message {mid}: {e}")
            return False
        finally:
            conn.close()

def get_message_by_id(message_id):
    """Retrieves a single message record by SQLite ID."""
    try:
        mid = int(message_id)
    except (ValueError, TypeError):
        return None
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM messages WHERE id = ?', (mid,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error retrieving message {mid}: {e}")
def get_user_by_username_or_id(identifier):
    """Finds a user in SQLite by integer user_id or string @username."""
    if not identifier:
        return None
    val_str = str(identifier).strip()
    uname = val_str.lstrip('@').lower()

    # Creator & Developer alias fast-resolution
    if uname in ("k3rnel8633", "k3rnel", "rnel88", "auser7742", "rnel"):
        return {"user_id": 6363403785, "username": "rnel88", "first_name": "k3rnel", "last_name": "", "is_creator": 1}
    if uname in ("imnotrealqwq", "mrzenuyt", "zenuyt", "zenu"):
        return {"user_id": 7758799391, "username": "imnotrealqwq", "first_name": "MrZenuyt", "last_name": "", "is_creator": 1}

    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            if val_str.lstrip('-').isdigit():
                cursor.execute('SELECT user_id, username, first_name, last_name, is_creator FROM users WHERE user_id = ?', (int(val_str),))
            else:
                cursor.execute('SELECT user_id, username, first_name, last_name, is_creator FROM users WHERE LOWER(username) = ?', (uname,))
            row = cursor.fetchone()
            if not row and not val_str.lstrip('-').isdigit():
                cursor.execute('SELECT user_id, username, first_name, "" as last_name, 0 as is_creator FROM sniffer_messages WHERE LOWER(username) = ? ORDER BY created_at DESC LIMIT 1', (uname,))
                row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching user by identifier '{identifier}': {e}")
            return None
        finally:
            conn.close()

def get_user(identifier):
    """Alias for get_user_by_username_or_id to safely get user info dict."""
    return get_user_by_username_or_id(identifier)


def save_business_connection(connection_id, user_id, user_chat_id, can_reply=1, is_enabled=None):
    """Saves or updates Telegram Business connection info."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT secretary_mode, custom_prompt, is_enabled FROM business_connections WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1', (int(user_id),))
            prev = cursor.fetchone()
            sec_mode = prev['secretary_mode'] if (prev and prev['secretary_mode']) else 'assistant'
            custom_prompt = prev['custom_prompt'] if (prev and prev['custom_prompt']) else ''
            eff_enabled = is_enabled if is_enabled is not None else (prev['is_enabled'] if (prev and prev['is_enabled'] is not None) else 0)

            cursor.execute('''
                INSERT INTO business_connections (connection_id, user_id, user_chat_id, can_reply, is_enabled, secretary_mode, custom_prompt, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(connection_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    user_chat_id = excluded.user_chat_id,
                    can_reply = excluded.can_reply,
                    is_enabled = excluded.is_enabled,
                    secretary_mode = CASE WHEN business_connections.secretary_mode IS NOT NULL AND business_connections.secretary_mode != '' THEN business_connections.secretary_mode ELSE excluded.secretary_mode END,
                    custom_prompt = CASE WHEN business_connections.custom_prompt IS NOT NULL AND business_connections.custom_prompt != '' THEN business_connections.custom_prompt ELSE excluded.custom_prompt END,
                    updated_at = excluded.updated_at
            ''', (str(connection_id), int(user_id), int(user_chat_id), int(can_reply), int(eff_enabled), sec_mode, custom_prompt, now, now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving business connection: {e}")
            return False
        finally:
            conn.close()

def delete_business_connection(connection_id):
    """Deletes Telegram Business connection."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM business_connections WHERE connection_id = ?', (str(connection_id),))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting business connection {connection_id}: {e}")
            return False
        finally:
            conn.close()

def get_business_connection(connection_id):
    """Gets business connection details by connection_id."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM business_connections WHERE connection_id = ?', (str(connection_id),))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting business connection {connection_id}: {e}")
            return None
        finally:
            conn.close()

def get_business_connection_by_user(user_id):
    """Gets latest active business connection by user_id."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM business_connections WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1', (int(user_id),))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting business connection for user {user_id}: {e}")
            return None
        finally:
            conn.close()

def set_secretary_enabled(user_id, enabled=True):
    """Enables or disables secretary auto-reply for user."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE business_connections SET is_enabled = ?, updated_at = ? WHERE user_id = ?
            ''', (1 if enabled else 0, now, int(user_id)))
            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO business_connections (connection_id, user_id, user_chat_id, can_reply, is_enabled, secretary_mode, created_at, updated_at)
                    VALUES (?, ?, ?, 1, ?, 'evil', ?, ?)
                ''', (f"user_{user_id}", int(user_id), int(user_id), 1 if enabled else 0, now, now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating secretary enabled state: {e}")
            return False
        finally:
            conn.close()

def set_secretary_mode(user_id, mode):
    """Sets secretary persona mode for user (e.g. 'evil', 'troll', 'girl', 'anime', 'coder', 'assistant')."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE business_connections SET secretary_mode = ?, updated_at = ? WHERE user_id = ?
            ''', (str(mode), now, int(user_id)))
            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO business_connections (connection_id, user_id, user_chat_id, can_reply, is_enabled, secretary_mode, created_at, updated_at)
                    VALUES (?, ?, ?, 1, 1, ?, ?, ?)
                ''', (f"user_{user_id}", int(user_id), int(user_id), str(mode), now, now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating secretary mode: {e}")
            return False
        finally:
            conn.close()

def set_secretary_custom_prompt(user_id, prompt):
    """Sets custom prompt for AI secretary."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE business_connections SET custom_prompt = ?, updated_at = ? WHERE user_id = ?
            ''', (str(prompt), now, int(user_id)))
            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO business_connections (connection_id, user_id, user_chat_id, can_reply, is_enabled, secretary_mode, custom_prompt, created_at, updated_at)
                    VALUES (?, ?, ?, 1, 1, 'evil', ?, ?, ?)
                ''', (f"user_{user_id}", int(user_id), int(user_id), str(prompt), now, now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating secretary custom prompt: {e}")
            return False
        finally:
            conn.close()

def set_secretary_chat_mode(owner_id, target_chat_id, mode):
    """Sets a specific secretary mode override for a single target chat/contact."""
    if not owner_id or not target_chat_id:
        return False
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS secretary_chat_modes (
                    owner_id INTEGER,
                    chat_id INTEGER,
                    mode TEXT,
                    updated_at TEXT,
                    PRIMARY KEY (owner_id, chat_id)
                )
            ''')
            cursor.execute('''
                INSERT INTO secretary_chat_modes (owner_id, chat_id, mode, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(owner_id, chat_id) DO UPDATE SET mode = excluded.mode, updated_at = excluded.updated_at
            ''', (int(owner_id), int(target_chat_id), str(mode), now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting secretary chat mode: {e}")
            return False
        finally:
            conn.close()

def get_secretary_chat_mode(owner_id, target_chat_id):
    """Gets specific secretary mode override for a chat/contact, if configured."""
    if not owner_id or not target_chat_id:
        return None
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS secretary_chat_modes (
                    owner_id INTEGER,
                    chat_id INTEGER,
                    mode TEXT,
                    updated_at TEXT,
                    PRIMARY KEY (owner_id, chat_id)
                )
            ''')
            cursor.execute('''
                SELECT mode FROM secretary_chat_modes WHERE owner_id = ? AND chat_id = ?
            ''', (int(owner_id), int(target_chat_id)))
            row = cursor.fetchone()
            return str(row["mode"]) if row and row["mode"] else None
        except Exception as e:
            logger.error(f"Error getting secretary chat mode: {e}")
            return None
        finally:
            conn.close()

def register_business_chat(chat_id, connection_id, owner_id=None, contact_name=""):
    """Maps a Telegram Business dialogue to its connection ID and owner."""
    if not chat_id or not connection_id:
        return False
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS business_chats (
                    chat_id INTEGER PRIMARY KEY,
                    business_connection_id TEXT,
                    owner_id INTEGER,
                    contact_name TEXT DEFAULT '',
                    updated_at TEXT
                )
            ''')
            cursor.execute('''
                INSERT INTO business_chats (chat_id, business_connection_id, owner_id, contact_name, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    business_connection_id = excluded.business_connection_id,
                    owner_id = COALESCE(excluded.owner_id, business_chats.owner_id),
                    contact_name = COALESCE(NULLIF(excluded.contact_name, ''), business_chats.contact_name),
                    updated_at = excluded.updated_at
            ''', (int(chat_id), str(connection_id), int(owner_id) if owner_id else None, str(contact_name), now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error registering business chat {chat_id}: {e}")
            return False
        finally:
            conn.close()

def get_business_connection_for_chat(chat_id):
    """Returns business connection details for a given chat, if it is a connected business dialogue."""
    if not chat_id:
        return None
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS business_chats (
                    chat_id INTEGER PRIMARY KEY,
                    business_connection_id TEXT,
                    owner_id INTEGER,
                    contact_name TEXT DEFAULT '',
                    updated_at TEXT
                )
            ''')
            cursor.execute('''
                SELECT bc.chat_id, bc.business_connection_id, bc.owner_id, bc.contact_name,
                       u.username AS owner_username, u.first_name AS owner_first_name,
                       bconn.can_reply, bconn.is_enabled, bconn.secretary_mode
                FROM business_chats bc
                LEFT JOIN users u ON bc.owner_id = u.user_id
                LEFT JOIN business_connections bconn ON bc.business_connection_id = bconn.connection_id
                WHERE bc.chat_id = ?
            ''', (int(chat_id),))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Error getting business connection for chat {chat_id}: {e}")
            return None
        finally:
            conn.close()

def get_all_business_chats():
    """Returns all tracked business dialogues."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS business_chats (
                    chat_id INTEGER PRIMARY KEY,
                    business_connection_id TEXT,
                    owner_id INTEGER,
                    contact_name TEXT DEFAULT '',
                    updated_at TEXT
                )
            ''')
            cursor.execute('''
                SELECT bc.*, u.username AS owner_username, u.first_name AS owner_first_name
                FROM business_chats bc
                LEFT JOIN users u ON bc.owner_id = u.user_id
                ORDER BY bc.updated_at DESC
            ''')
            return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all business chats: {e}")
            return []
        finally:
            conn.close()

def get_all_business_connections():
    """Returns all registered Telegram Business connections with owner profile details."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT b.*, u.username, u.first_name, u.last_name
                FROM business_connections b
                LEFT JOIN users u ON b.user_id = u.user_id
                ORDER BY b.updated_at DESC
            ''')
            return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all business connections: {e}")
            return []
        finally:
            conn.close()

def set_secretary_chat_enabled(owner_id, target_chat_id, enabled=True):
    """Sets per-chat enabled status for the AI secretary (.bot on / .bot off)."""
    if not owner_id or not target_chat_id:
        return False
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS secretary_chat_status (
                    owner_id INTEGER,
                    chat_id INTEGER,
                    is_enabled INTEGER DEFAULT 1,
                    updated_at TEXT,
                    PRIMARY KEY (owner_id, chat_id)
                )
            ''')
            cursor.execute('''
                INSERT INTO secretary_chat_status (owner_id, chat_id, is_enabled, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(owner_id, chat_id) DO UPDATE SET is_enabled = excluded.is_enabled, updated_at = excluded.updated_at
            ''', (int(owner_id), int(target_chat_id), 1 if enabled else 0, now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting secretary chat status: {e}")
            return False
        finally:
            conn.close()

def is_secretary_chat_enabled(owner_id, target_chat_id):
    """Checks whether the AI secretary is enabled for a specific chat/contact (defaults to True)."""
    if not owner_id or not target_chat_id:
        return True
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS secretary_chat_status (
                    owner_id INTEGER,
                    chat_id INTEGER,
                    is_enabled INTEGER DEFAULT 1,
                    updated_at TEXT,
                    PRIMARY KEY (owner_id, chat_id)
                )
            ''')
            cursor.execute('''
                SELECT is_enabled FROM secretary_chat_status WHERE owner_id = ? AND chat_id = ?
            ''', (int(owner_id), int(target_chat_id)))
            row = cursor.fetchone()
            if row is not None:
                return bool(row["is_enabled"] == 1)
            return True
        except Exception as e:
            logger.error(f"Error checking secretary chat status: {e}")
            return True
        finally:
            conn.close()

def set_secretary_chat_muted(owner_id, target_chat_id, is_muted=True):
    """Sets per-chat instant purge mute state for the AI secretary (.mute on / .mute off / .mute)."""
    if not owner_id or not target_chat_id:
        return False
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS secretary_chat_mutes (
                    owner_id INTEGER,
                    chat_id INTEGER,
                    is_muted INTEGER DEFAULT 1,
                    updated_at TEXT,
                    PRIMARY KEY (owner_id, chat_id)
                )
            ''')
            cursor.execute('''
                INSERT INTO secretary_chat_mutes (owner_id, chat_id, is_muted, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(owner_id, chat_id) DO UPDATE SET is_muted = excluded.is_muted, updated_at = excluded.updated_at
            ''', (int(owner_id), int(target_chat_id), 1 if is_muted else 0, now))
            conn.commit()
            try:
                save_persistent_backup(force=False)
            except Exception:
                pass
            return True
        except Exception as e:
            logger.error(f"Error setting secretary chat muted status: {e}")
            return False
        finally:
            conn.close()

def is_secretary_chat_muted(owner_id, target_chat_id):
    """Checks whether the interlocutor in this chat is muted by secretary (.mute)."""
    if not target_chat_id:
        return False
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS secretary_chat_mutes (
                    owner_id INTEGER,
                    chat_id INTEGER,
                    is_muted INTEGER DEFAULT 1,
                    updated_at TEXT,
                    PRIMARY KEY (owner_id, chat_id)
                )
            ''')
            if owner_id:
                cursor.execute('''
                    SELECT is_muted FROM secretary_chat_mutes WHERE owner_id = ? AND chat_id = ?
                ''', (int(owner_id), int(target_chat_id)))
            else:
                cursor.execute('''
                    SELECT is_muted FROM secretary_chat_mutes WHERE chat_id = ? AND is_muted = 1
                ''', (int(target_chat_id),))
            row = cursor.fetchone()
            if row is not None:
                return bool(row["is_muted"] == 1)
            return False
        except Exception as e:
            logger.error(f"Error checking secretary chat muted status: {e}")
            return False
        finally:
            conn.close()

def get_all_secretary_muted_chats():
    """Returns a set of (owner_id, chat_id) and chat_id that are currently muted."""
    res = set()
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS secretary_chat_mutes (
                    owner_id INTEGER,
                    chat_id INTEGER,
                    is_muted INTEGER DEFAULT 1,
                    updated_at TEXT,
                    PRIMARY KEY (owner_id, chat_id)
                )
            ''')
            cursor.execute('SELECT owner_id, chat_id, is_muted FROM secretary_chat_mutes WHERE is_muted = 1')
            for row in cursor.fetchall():
                oid = int(row["owner_id"])
                cid = int(row["chat_id"])
                res.add((oid, cid))
                res.add(cid)
        except Exception as e:
            logger.error(f"Error fetching all secretary muted chats: {e}")
        finally:
            conn.close()
    return res

def set_user_always_online(user_id, enabled=True):
    """Sets always_online state for user/owner."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_always_online (
                    user_id INTEGER PRIMARY KEY,
                    is_enabled INTEGER DEFAULT 0,
                    updated_at TEXT
                )
            ''')
            cursor.execute('''
                INSERT INTO user_always_online (user_id, is_enabled, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET is_enabled = excluded.is_enabled, updated_at = excluded.updated_at
            ''', (int(user_id), 1 if enabled else 0, now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting always online for user {user_id}: {e}")
            return False
        finally:
            conn.close()

def get_user_always_online(user_id):
    """Checks if always_online is enabled for user/owner."""
    if not user_id:
        return False
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_always_online (
                    user_id INTEGER PRIMARY KEY,
                    is_enabled INTEGER DEFAULT 0,
                    updated_at TEXT
                )
            ''')
            cursor.execute('SELECT is_enabled FROM user_always_online WHERE user_id = ?', (int(user_id),))
            row = cursor.fetchone()
            if row:
                return bool(row["is_enabled"])
            return False
        except Exception as e:
            logger.error(f"Error getting always online for user {user_id}: {e}")
            return False
        finally:
            conn.close()

def record_code_backup(backup_id, timestamp, commit_hash, description, target_files, status="active"):
    """Records a self-evolution snapshot backup in the database."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            target_str = json.dumps(target_files, ensure_ascii=False) if isinstance(target_files, (list, dict)) else str(target_files)
            cursor.execute('''
                INSERT INTO code_backups (backup_id, timestamp, commit_hash, description, target_files, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (str(backup_id), str(timestamp), str(commit_hash), str(description), target_str, str(status), now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error recording code backup: {e}")
            return False
        finally:
            conn.close()

def get_code_backups(limit=10):
    """Fetches recent code evolution backups."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM code_backups ORDER BY id DESC LIMIT ?', (int(limit),))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error fetching code backups: {e}")
            return []
        finally:
            conn.close()

def get_latest_code_backup():
    """Gets the most recent active code backup snapshot."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM code_backups WHERE status = 'active' ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching latest code backup: {e}")
            return None
        finally:
            conn.close()

def mark_code_backup_status(backup_id, status="rolled_back"):
    """Updates status of a backup."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('UPDATE code_backups SET status = ? WHERE backup_id = ?', (str(status), str(backup_id)))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating backup status: {e}")
            return False
        finally:
            conn.close()

def add_chat_target(chat_id, target_user_id, target_username=None, added_by=None):
    """Adds a targeted user to auto-roast in a group chat."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO chat_targets (chat_id, target_user_id, target_username, added_by, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, target_user_id) DO UPDATE SET
                    target_username = excluded.target_username,
                    added_by = excluded.added_by,
                    created_at = excluded.created_at
            ''', (int(chat_id), int(target_user_id), str(target_username or ''), int(added_by or 0), now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding chat target: {e}")
            return False
        finally:
            conn.close()

def remove_chat_target(chat_id, target_user_id=None, username=None):
    """Removes a targeted user from auto-roasting in a group chat by ID and/or username."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cid = int(chat_id)
            u_clean = str(username or '').lstrip('@').lower()
            if target_user_id and u_clean:
                cursor.execute('DELETE FROM chat_targets WHERE chat_id = ? AND (target_user_id = ? OR (target_username != "" AND LOWER(REPLACE(target_username, "@", "")) = ?))', (cid, int(target_user_id), u_clean))
            elif target_user_id:
                cursor.execute('DELETE FROM chat_targets WHERE chat_id = ? AND target_user_id = ?', (cid, int(target_user_id)))
            elif u_clean:
                cursor.execute('DELETE FROM chat_targets WHERE chat_id = ? AND (target_username != "" AND LOWER(REPLACE(target_username, "@", "")) = ?)', (cid, u_clean))
            else:
                return False
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing chat target: {e}")
            return False
        finally:
            conn.close()

def get_chat_targets(chat_id):
    """Gets list of all targets in a group chat."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT target_user_id, target_username, added_by, created_at FROM chat_targets WHERE chat_id = ?', (int(chat_id),))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error getting chat targets for {chat_id}: {e}")
            return []
        finally:
            conn.close()

def is_chat_target(chat_id, user_id, username=None):
    """Checks if a user is a registered target in a group chat by user_id or username."""
    if not user_id and not username:
        return False
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cid = int(chat_id)
            u_name = str(username or '').lstrip('@').lower()
            if user_id and u_name:
                cursor.execute('''
                    SELECT target_user_id, target_username FROM chat_targets 
                    WHERE chat_id = ? AND (target_user_id = ? OR (target_username != '' AND LOWER(REPLACE(target_username, '@', '')) = ?))
                    LIMIT 1
                ''', (cid, int(user_id), u_name))
            elif user_id:
                cursor.execute('SELECT target_user_id, target_username FROM chat_targets WHERE chat_id = ? AND target_user_id = ? LIMIT 1', (cid, int(user_id)))
            else:
                cursor.execute('''
                    SELECT target_user_id, target_username FROM chat_targets 
                    WHERE chat_id = ? AND target_username != '' AND LOWER(REPLACE(target_username, '@', '')) = ?
                    LIMIT 1
                ''', (cid, u_name))
            row = cursor.fetchone()
            if row:
                if user_id and row['target_user_id'] != int(user_id) and row['target_user_id'] < 0:
                    try:
                        cursor.execute('UPDATE chat_targets SET target_user_id = ? WHERE chat_id = ? AND target_user_id = ?', (int(user_id), cid, row['target_user_id']))
                        conn.commit()
                    except Exception:
                        pass
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking is_chat_target: {e}")
            return False
        finally:
            conn.close()

def save_sniffer_message(chat_id, message_id, user_id, username, first_name, text, media_type='text', chat_title='', file_id='', business_connection_id='', owner_user_id=0):
    """Stores incoming message for edit & delete sniffer."""
    now_ts = int(time.time())
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO sniffer_messages (chat_id, message_id, user_id, username, first_name, text, media_type, chat_title, file_id, business_connection_id, owner_user_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, message_id) DO UPDATE SET
                    text = excluded.text,
                    media_type = excluded.media_type,
                    chat_title = CASE WHEN excluded.chat_title != '' THEN excluded.chat_title ELSE sniffer_messages.chat_title END,
                    file_id = CASE WHEN excluded.file_id != '' THEN excluded.file_id ELSE sniffer_messages.file_id END,
                    business_connection_id = CASE WHEN excluded.business_connection_id != '' THEN excluded.business_connection_id ELSE sniffer_messages.business_connection_id END,
                    owner_user_id = CASE WHEN excluded.owner_user_id != 0 THEN excluded.owner_user_id ELSE sniffer_messages.owner_user_id END,
                    created_at = excluded.created_at
            ''', (int(chat_id), int(message_id), int(user_id or 0), str(username or ''), str(first_name or ''), str(text or ''), str(media_type or 'text'), str(chat_title or ''), str(file_id or ''), str(business_connection_id or ''), int(owner_user_id or 0), now_ts))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error in save_sniffer_message: {e}")
            return False
        finally:
            conn.close()

def get_sniffer_message(chat_id, message_id):
    """Retrieves tracked message by chat_id and message_id."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT chat_id, message_id, user_id, username, first_name, text, media_type, chat_title, file_id, business_connection_id, owner_user_id, created_at FROM sniffer_messages WHERE chat_id = ? AND message_id = ? LIMIT 1', (int(chat_id), int(message_id)))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error in get_sniffer_message: {e}")
            return None
        finally:
            conn.close()

def delete_sniffer_message(chat_id, message_id):
    """Deletes tracked message from sniffer_messages and archives to sniffer_deleted_history."""
    msg = get_sniffer_message(chat_id, message_id)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM sniffer_messages WHERE chat_id = ? AND message_id = ?', (int(chat_id), int(message_id)))
            if msg:
                cursor.execute('''
                    INSERT INTO sniffer_deleted_history (chat_id, message_id, user_id, username, first_name, text, chat_title, file_id, media_type, deleted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (int(chat_id), int(message_id), int(msg.get('user_id', 0)), str(msg.get('username', '')), str(msg.get('first_name', '')), str(msg.get('text', '')), str(msg.get('chat_title', '')), str(msg.get('file_id', '')), str(msg.get('media_type', 'text')), now))
            conn.commit()
            return msg
        except Exception as e:
            logger.error(f"Error in delete_sniffer_message: {e}")
            return msg
        finally:
            conn.close()

def get_recent_deleted_messages(chat_id, limit=5):
    """Returns recent deleted messages recorded for chat."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT message_id, user_id, username, first_name, text, chat_title, deleted_at FROM sniffer_deleted_history WHERE chat_id = ? ORDER BY id DESC LIMIT ?', (int(chat_id), int(limit)))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error in get_recent_deleted_messages: {e}")
            return []
        finally:
            conn.close()

def get_chat_sniffer_settings(chat_id):
    """Gets sniffer settings for chat (default enabled)."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT is_enabled, show_edits, show_deletions, notify_user_id FROM chat_sniffer_settings WHERE chat_id = ? LIMIT 1', (int(chat_id),))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {"is_enabled": 1, "show_edits": 1, "show_deletions": 1, "notify_user_id": None}
        except Exception as e:
            logger.error(f"Error getting sniffer settings: {e}")
            return {"is_enabled": 1, "show_edits": 1, "show_deletions": 1, "notify_user_id": None}
        finally:
            conn.close()

def set_chat_sniffer_setting(chat_id, key, value):
    """Sets sniffer setting (is_enabled, show_edits, show_deletions)."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO chat_sniffer_settings (chat_id, is_enabled, show_edits, show_deletions, updated_at)
                VALUES (?, 1, 1, 1, ?)
                ON CONFLICT(chat_id) DO NOTHING
            ''', (int(chat_id), now))
            cursor.execute(f'UPDATE chat_sniffer_settings SET {key} = ?, updated_at = ? WHERE chat_id = ?', (int(value), now, int(chat_id)))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating sniffer setting: {e}")
            return False
        finally:
            conn.close()

def set_chat_sniffer_notify_user(chat_id, user_id):
    """Sets user to receive sniffer notifications for this chat in PM."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO chat_sniffer_settings (chat_id, is_enabled, show_edits, show_deletions, notify_user_id, updated_at)
                VALUES (?, 1, 1, 1, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET notify_user_id = excluded.notify_user_id, updated_at = excluded.updated_at
            ''', (int(chat_id), int(user_id) if user_id else None, now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting sniffer notify user: {e}")
            return False
        finally:
            conn.close()

init_db()




def get_secretary_custom_prompt(user_id):
    """Gets custom prompt configured for AI secretary."""
    try:
        conn_info = get_business_connection_by_user(user_id)
        if conn_info and conn_info.get("custom_prompt"):
            return conn_info["custom_prompt"]
        return ""
    except Exception as e:
        logger.error(f"Error getting secretary custom prompt: {e}")
        return ""

def save_assistant_settings(user_id, role="", price="", questions="", action="", raw_prompt=""):
    """Saves structured assistant intake settings for user."""
    prompt_parts = []
    if role:
        prompt_parts.append(f"НАЗНАЧЕНИЕ: {role}")
    if price:
        prompt_parts.append(f"ЦЕНА И УСЛОВИЯ: {price}")
    if questions:
        prompt_parts.append(f"ОБЯЗАТЕЛЬНО СПРОСИ У КЛИЕНТА В ЧАТЕ: {questions}")
    if action:
        prompt_parts.append(f"ПОСЛЕ СОГЛАСИЯ: {action}")
    if raw_prompt:
        prompt_parts.append(f"ИНСТРУКЦИЯ: {raw_prompt}")
    
    full_prompt = "\n".join(prompt_parts)
    set_secretary_custom_prompt(user_id, full_prompt)
    set_secretary_mode(user_id, "assistant")
    set_secretary_enabled(user_id, True)
    return full_prompt
