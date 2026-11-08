# -*- coding: utf-8 -*-
"""
db_sync.py — Персистентность базы данных между деплоями Render.

Render web-сервисы имеют эфемерный диск: каждый деплой/рестарт откатывает
chats.db к состоянию из git-репозитория. Этот модуль решает проблему:

1) При старте: скачивает свежий chats_persistent_backup.json с ветки data-sync
   в GitHub (через Contents API — git-клиент в контейнере не нужен) и
   восстанавливает его поверх локальной базы (restore с полным набором таблиц,
   включая business_connections / business_chats, которые старый
   restore_persistent_backup не покрывал).
2) В фоне: каждые DB_SYNC_INTERVAL секунд сохраняет дамп базы и пушит его
   в ветку data-sync через GitHub API. Ветка data-sync НЕ связана с
   авто-деплоем Render (деплой смотрит только на main), поэтому пуш данных
   никогда не перезапускает контейнер.
"""

import os
import time
import base64
import logging
import threading

import requests

import config

logger = logging.getLogger(__name__)

DB_SYNC_BRANCH = os.getenv("DB_SYNC_BRANCH", "data-sync")
DB_SYNC_INTERVAL = int(os.getenv("DB_SYNC_INTERVAL", "900"))  # 15 минут
import hashlib
_last_pushed_hash = None
_last_pushed_sha = None
_initial_remote_checked = False
DB_SYNC_FILE = "chats_persistent_backup.json"

_GITHUB_TOKEN = None
_repo_cache = None
_sync_thread = None
_sync_running = False
_last_push_result = {"ok": False, "error": "ещё не выполнялся", "ts": None}


def _get_token():
    global _GITHUB_TOKEN
    if _GITHUB_TOKEN:
        return _GITHUB_TOKEN
    _GITHUB_TOKEN = (
        os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        or os.getenv("GIT_TOKEN") or os.getenv("GITHUB_PAT")
        or getattr(config, "GITHUB_TOKEN", "")
    )
    return _GITHUB_TOKEN


def _get_repo():
    global _repo_cache
    if _repo_cache:
        return _repo_cache
    _repo_cache = getattr(config, "GITHUB_REPO", "")
    return _repo_cache


def _api_headers():
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "db-sync-module",
    }


def fetch_remote_backup():
    """Скачивает JSON-бэкап с ветки data-sync. Возвращает dict или None."""
    repo = _get_repo()
    if not repo:
        return None

    # 1. Direct CDN raw URL with authorization (fastest, supports any file size)
    try:
        raw_url = f"https://raw.githubusercontent.com/{repo}/{DB_SYNC_BRANCH}/{DB_SYNC_FILE}?t={int(time.time())}"
        r = requests.get(raw_url, headers=_api_headers(), timeout=25)
        if r.status_code == 200 and r.text.strip():
            import json
            return json.loads(r.text)
    except Exception as _raw_e:
        logger.debug(f"db_sync: raw download attempt notice: {_raw_e}")

    # 2. GitHub REST API fallback
    url = (f"https://api.github.com/repos/{repo}/contents/{DB_SYNC_FILE}"
           f"?ref={DB_SYNC_BRANCH}&t={int(time.time())}")
    try:
        r = requests.get(url, headers=_api_headers(), timeout=25)
        if r.status_code == 200:
            data = r.json()
            # If download_url provided in metadata
            download_url = data.get("download_url")
            if download_url:
                try:
                    raw = requests.get(download_url, headers=_api_headers(), timeout=35)
                    if raw.status_code == 200 and raw.text.strip():
                        import json
                        return json.loads(raw.text)
                except Exception:
                    pass

            # Base64 content if file is small
            content = data.get("content")
            if isinstance(content, str) and content.strip():
                try:
                    if data.get("encoding") == "base64":
                        decoded = base64.b64decode(content).decode("utf-8")
                    else:
                        decoded = content
                    import json
                    return json.loads(decoded)
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"db_sync: fetch_remote_backup fallback failed: {e}")
    return None


def restore_from_remote(reason="startup"):
    """Тянет удалённый бэкап и восстанавливает его в SQLite базу."""
    import database
    payload = fetch_remote_backup()
    if not payload or not isinstance(payload, dict):
        logger.warning(f"db_sync: remote restore skipped ({reason}, no data)")
        return False
    try:
        database.restore_backup_payload(payload)
        n_users = len(payload.get("users", []))
        n_msgs = len(payload.get("messages", []))
        logger.info(f"db_sync: restored from data-sync branch ({reason}): "
                    f"{n_users} users, {n_msgs} messages, saved_at={payload.get('_saved_at')}")
        return True
    except Exception as e:
        logger.error(f"db_sync: restore_from_remote failed: {e}")
        return False


_remote_disabled = True

def push_backup_to_remote():
    global _remote_disabled
    if _remote_disabled:
        try:
            import database
            database.save_persistent_backup(force=True)
        except Exception:
            pass
        return True
    """Сохраняет дамп базы и пушит его в ветку data-sync через GitHub API с защитой от перезаписи большим дампом."""
    import database
    global _last_push_result
    repo = _get_repo()
    if not repo:
        return False
    try:
        database.save_persistent_backup(force=True)
        if not os.path.exists(database.BACKUP_JSON_PATH):
            return False

        import json
        with open(database.BACKUP_JSON_PATH, "r", encoding="utf-8") as f:
            local_payload = json.load(f)

        local_u_cnt = len(local_payload.get("users", []))
        local_m_cnt = len(local_payload.get("messages", []))

        global _last_pushed_hash, _initial_remote_checked
        content_raw = json.dumps(local_payload, ensure_ascii=False, indent=2).encode("utf-8")
        content_hash = hashlib.sha256(content_raw).hexdigest()

        # Bandwidth Saver: Skip push if database has not changed at all since last push!
        if _last_pushed_hash and content_hash == _last_pushed_hash:
            logger.debug("db_sync: database unchanged, skipping upload to save bandwidth.")
            return True

        # Anti-shrink guard: check remote only once on first push or if local database is completely empty
        if not _initial_remote_checked or (local_u_cnt == 0 and local_m_cnt == 0):
            _initial_remote_checked = True
            remote_data = fetch_remote_backup()
            if remote_data:
                rem_u_cnt = len(remote_data.get("users", []))
                rem_m_cnt = len(remote_data.get("messages", []))
                rem_mod_cnt = len(remote_data.get("moderation_data", {}).get("chats", {})) if isinstance(remote_data.get("moderation_data"), dict) else 0
                local_mod_cnt = len(local_payload.get("moderation_data", {}).get("chats", {})) if isinstance(local_payload.get("moderation_data"), dict) else 0
                rem_am_cnt = len(remote_data.get("chat_automod", []))
                local_am_cnt = len(local_payload.get("chat_automod", []))

                if rem_u_cnt > local_u_cnt or rem_m_cnt > local_m_cnt or rem_mod_cnt > local_mod_cnt or rem_am_cnt > local_am_cnt:
                    logger.warning(f"db_sync: merging remote data (u:{rem_u_cnt}, m:{rem_m_cnt}, mod:{rem_mod_cnt}, am:{rem_am_cnt}) into local before push!")
                    database.restore_backup_payload(remote_data)
                    database.save_persistent_backup(force=True)
                    with open(database.BACKUP_JSON_PATH, "r", encoding="utf-8") as f:
                        local_payload = json.load(f)
                    content_raw = json.dumps(local_payload, ensure_ascii=False, indent=2).encode("utf-8")
                    content_hash = hashlib.sha256(content_raw).hexdigest()

        content_raw = json.dumps(local_payload, ensure_ascii=False, indent=2).encode("utf-8")
        content_b64 = base64.b64encode(content_raw).decode("ascii")

        api = "https://api.github.com"
        # Текущий sha файла на ветке (для обновления, а не конфликта)
        global _last_pushed_sha
        file_sha = _last_pushed_sha
        for _att in range(2):
            try:
                r = requests.get(f"{api}/repos/{repo}/contents/{DB_SYNC_FILE}?ref={DB_SYNC_BRANCH}",
                                 headers=_api_headers(), timeout=40)
                if r.status_code == 200:
                    file_sha = r.json().get("sha")
                    break
            except Exception:
                time.sleep(1)

        body = {
            "message": f"chore(data): auto backup {time.strftime('%Y-%m-%d %H:%M')}",
            "content": content_b64,
            "branch": DB_SYNC_BRANCH,
        }
        if file_sha:
            body["sha"] = file_sha
        r = requests.put(f"{api}/repos/{repo}/contents/{DB_SYNC_FILE}",
                         headers=_api_headers(), json=body, timeout=60)
        ok = r.status_code in (200, 201)
        if ok:
            _last_pushed_hash = content_hash
            try:
                _last_pushed_sha = r.json().get("content", {}).get("sha")
            except Exception:
                pass
        _last_push_result = {"ok": ok, "error": None if ok else f"HTTP {r.status_code}",
                             "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
        if not ok:
            logger.warning(f"db_sync: push failed: HTTP {r.status_code} {r.text[:200]}")
        return ok
    except Exception as e:
        _last_push_result = {"ok": False, "error": str(e), "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
        logger.warning(f"db_sync: push_backup_to_remote failed: {e}")
        return False


def get_sync_status():
    """Статистика для панели Создателя."""
    return {
        "branch": DB_SYNC_BRANCH,
        "interval_sec": DB_SYNC_INTERVAL,
        "last_push": _last_push_result,
    }


def _sync_loop():
    global _sync_running
    _sync_running = True
    # Первый пуш сразу после старта — закрепляем текущее состояние базы
    time.sleep(60)
    while _sync_running:
        try:
            push_backup_to_remote()
        except Exception as e:
            logger.warning(f"db_sync loop error: {e}")
        time.sleep(DB_SYNC_INTERVAL)


def start_db_sync():
    """Запускает фоновую синхронизацию базы с веткой data-sync."""
    global _sync_thread
    if _sync_thread and _sync_thread.is_alive():
        return
    _sync_thread = threading.Thread(target=_sync_loop, daemon=True, name="db_sync_loop")
    _sync_thread.start()
    logger.info(f"db_sync: background push loop started (every {DB_SYNC_INTERVAL}s to branch {DB_SYNC_BRANCH})")

_fast_sync_timer = None
_fast_sync_lock = threading.Lock()

def trigger_fast_sync(delay_sec=3.0):
    """Schedules a debounced push to GitHub data-sync within delay_sec seconds."""
    global _fast_sync_timer
    with _fast_sync_lock:
        if _fast_sync_timer and _fast_sync_timer.is_alive():
            try:
                _fast_sync_timer.cancel()
            except Exception:
                pass

        def _run_fast_push():
            try:
                push_backup_to_remote()
            except Exception as e:
                logger.debug(f"Fast sync execution notice: {e}")

        _fast_sync_timer = threading.Timer(delay_sec, _run_fast_push)
        _fast_sync_timer.daemon = True
        _fast_sync_timer.start()
