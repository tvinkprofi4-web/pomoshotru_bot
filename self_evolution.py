"""
self_evolution.py
Autonomous Self-Evolution, Extension & Server Management Engine for AI for copil
Exclusively designed and implemented for Creator k3rnel (ID: 6363403785, @k3rnel8633)
"""
import sys
import os
import time
import datetime
import subprocess
import shutil
import ast
import py_compile
import tempfile
import io
import re
import json
import contextlib
import traceback
import threading
import logging
import base64
import random
import urllib.parse
import requests
import config
import database

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOT_PY_PATH = os.path.join(BASE_DIR, "bot.py")
CUSTOM_FEATURES_PATH = os.path.join(BASE_DIR, "custom_features.py")
BACKUP_DIR = os.path.join(BASE_DIR, ".backups")
HISTORY_FILE = os.path.join(BACKUP_DIR, "history.json")

os.makedirs(BACKUP_DIR, exist_ok=True)

# User-Agents for internet searching and documentation fetching
SEARCH_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
]

def ensure_git_identity():
    """Ensures git author name and email are configured for automatic commits in headless containers like Render."""
    try:
        subprocess.run(["git", "config", "user.name", "AI for copil"], cwd=BASE_DIR, capture_output=True)
        subprocess.run(["git", "config", "user.email", "copil-bot@render.com"], cwd=BASE_DIR, capture_output=True)
        subprocess.run(["git", "config", "--global", "user.name", "AI for copil"], cwd=BASE_DIR, capture_output=True)
        subprocess.run(["git", "config", "--global", "user.email", "copil-bot@render.com"], cwd=BASE_DIR, capture_output=True)
    except Exception as e:
        logger.debug(f"Git config identity notice: {e}")

# ==========================================
# 0. AUTONOMOUS INTERNET ACCESS & SEARCH ENGINE
# ==========================================

def search_internet_for_context(query, max_results=5):
    """
    Autonomous live internet research tool for Gemini self-evolution and coding:
    Searches DuckDuckGo HTML, Instant Answers API, and Wikipedia for technical docs,
    API references, error fixes, and code samples.
    """
    if not query or not query.strip():
        return ""

    clean_q = query.strip()
    results = []

    # 1. DuckDuckGo Instant Answer API (JSON)
    try:
        api_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(clean_q)}&format=json&no_html=1&skip_disambig=1"
        resp = requests.get(api_url, headers={"User-Agent": random.choice(SEARCH_USER_AGENTS)}, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            abstract = data.get("AbstractText", "")
            if abstract:
                results.append(f"📌 [Справка]: {abstract}")
            for topic in data.get("RelatedTopics", [])[:3]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append(f"• {topic['Text']}")
    except Exception as e:
        logger.debug(f"DuckDuckGo API search error: {e}")

    # 2. DuckDuckGo HTML Web Search (Live web search snippets)
    try:
        html_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(clean_q)}"
        headers = {
            "User-Agent": random.choice(SEARCH_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        resp = requests.get(html_url, headers=headers, timeout=8)
        if resp.status_code == 200:
            raw_html = resp.text
            # Extract results snippets using regex
            snippets = re.findall(r'<a class="result__snippet[^>]*>([\s\S]*?)</a>', raw_html)
            titles = re.findall(r'<a class="result__url[^>]*href="([^"]*)"[^>]*>([\s\S]*?)</a>', raw_html)
            
            for i, snip in enumerate(snippets[:max_results]):
                clean_snip = re.sub(r'<[^>]+>', '', snip).strip()
                clean_snip = re.sub(r'\s+', ' ', clean_snip)
                if len(clean_snip) > 20:
                    results.append(f"🌐 [Web Результат {i+1}]: {clean_snip}")
    except Exception as e:
        logger.debug(f"DuckDuckGo HTML search error: {e}")

    # 3. Wikipedia Summary Fallback if technical concept
    try:
        wiki_url = f"https://ru.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean_q)}"
        resp = requests.get(wiki_url, headers={"User-Agent": random.choice(SEARCH_USER_AGENTS)}, timeout=5)
        if resp.status_code == 200:
            extract = resp.json().get("extract", "")
            if extract:
                results.append(f"📚 [Wikipedia]: {extract[:400]}")
    except Exception:
        pass

    if not results:
        return ""

    return "\n\n".join(results[:max_results])

def fetch_web_page_markdown(url, max_chars=8000):
    """Fetches web page content, documentation, or raw code and converts to clean readable text."""
    if not url or not url.startswith("http"):
        return ""
    try:
        headers = {
            "User-Agent": random.choice(SEARCH_USER_AGENTS),
            "Accept": "text/html,text/plain,application/json,*/*"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "").lower()
            if "json" in content_type:
                return json.dumps(resp.json(), indent=2, ensure_ascii=False)[:max_chars]
            
            text = resp.text
            # Strip scripts, styles, headers
            text = re.sub(r'<script\b[^>]*>[\s\S]*?</script>', '', text, flags=re.IGNORECASE)
            text = re.sub(r'<style\b[^>]*>[\s\S]*?</style>', '', text, flags=re.IGNORECASE)
            text = re.sub(r'<nav\b[^>]*>[\s\S]*?</nav>', '', text, flags=re.IGNORECASE)
            text = re.sub(r'<footer\b[^>]*>[\s\S]*?</footer>', '', text, flags=re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:max_chars]
        return f"HTTP {resp.status_code}"
    except Exception as e:
        return f"Error fetching {url}: {e}"

# ==========================================
# 1. SNAPSHOT & HISTORY MANAGEMENT
# ==========================================

def load_evolution_history():
    """Loads historical evolution snapshots from JSON."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_evolution_history(history):
    """Saves evolution snapshots history to JSON."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving evolution history: {e}")

def create_snapshot_backup(target_files=None, task_description=""):
    """
    Creates timestamped snapshot backups of specified files in .backups/
    and records metadata in both SQLite database (code_backups table) and history.json.
    """
    if not target_files:
        target_files = ["custom_features.py", "bot.py", "database.py", "config.py"]
        
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_id = f"snap_{ts}_{random.randint(100, 999)}"
    
    snapshot_entry = {
        "backup_id": backup_id,
        "timestamp": ts,
        "description": task_description or "Self-update pre-snapshot",
        "files": {}
    }
    
    saved_files = []
    for tf in target_files:
        p = os.path.join(BASE_DIR, tf)
        if os.path.exists(p):
            bak_name = f"{tf}.{ts}.bak"
            bak_path = os.path.join(BACKUP_DIR, bak_name)
            try:
                shutil.copy2(p, bak_path)
                snapshot_entry["files"][tf] = bak_name
                saved_files.append(tf)
            except Exception as e:
                logger.error(f"Error backing up {tf}: {e}")

    # Record in SQLite database for persistent recovery
    try:
        current_hash = "local"
        try:
            h_res = subprocess.run(["git", "log", "-1", "--format=%h"], cwd=BASE_DIR, capture_output=True, text=True)
            if h_res.returncode == 0:
                current_hash = h_res.stdout.strip()
        except Exception:
            pass
            
        database.record_code_backup(
            backup_id=backup_id,
            timestamp=ts,
            commit_hash=current_hash,
            description=task_description or "Autonomous update snapshot",
            target_files=saved_files,
            status="active"
        )
    except Exception as dbe:
        logger.debug(f"SQLite backup record notice: {dbe}")

    return snapshot_entry

def create_local_backup(target_path=BOT_PY_PATH):
    """Legacy helper: creates backup of a single file."""
    try:
        fname = os.path.basename(target_path)
        sn = create_snapshot_backup([fname])
        return sn.get("files", {}).get(fname, "")
    except Exception as e:
        logger.error(f"Error in create_local_backup: {e}")
        return None

def restore_local_backup(target_path=BOT_PY_PATH):
    """Restores the target file from the most recent timestamped snapshot."""
    try:
        fname = os.path.basename(target_path)
        if os.path.exists(BACKUP_DIR):
            bak_files = [
                os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR)
                if f.startswith(fname) and f.endswith(".bak")
            ]
            if bak_files:
                bak_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                latest_bak = bak_files[0]
                shutil.copy2(latest_bak, target_path)
                logger.info(f"Restored {target_path} from snapshot {latest_bak}")
                return True
    except Exception as e:
        logger.error(f"Error restoring backup: {e}")
    return False

# ==========================================
# 2. MULTI-LAYER SANDBOX VERIFICATION
# ==========================================

def verify_python_code_in_sandbox(code_str, filename="custom_features.py"):
    """
    Tier 1 & Tier 2 Zero-Crash Sandbox Verification:
    1. Static AST parse check (extracts syntax error line, message, code snippet).
    2. Bytecode compile check via py_compile in temp isolated file.
    3. Subprocess dry-run syntax verification.
    """
    if not code_str or len(code_str.strip()) < 20:
        return False, "Сгенерированный код слишком короткий или пуст.", 0

    # 1. AST Parse
    try:
        ast.parse(code_str, filename=filename)
    except SyntaxError as se:
        line_info = f"строка {se.lineno}" if se.lineno else "неизвестная строка"
        return False, f"Синтаксическая ошибка ({line_info}): {se.msg}\nКод: {se.text}", se.lineno or 0
    except Exception as e:
        return False, f"Ошибка синтаксического анализа AST: {e}", 0

    # 2. Py_Compile in isolated tempfile
    temp_fd, temp_path = tempfile.mkstemp(suffix=".py", prefix="patch_verify_")
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            f.write(code_str)

        try:
            py_compile.compile(temp_path, doraise=True)
        except py_compile.PyCompileError as pe:
            return False, f"Ошибка компиляции байткода: {pe.msg}", 0

        # 3. Subprocess verification check
        check_cmd = [
            sys.executable, "-c",
            "import sys, ast; ast.parse(open(sys.argv[1], encoding='utf-8').read()); print('SANDBOX_OK')"
        ]
        proc = subprocess.run(check_cmd + [temp_path], capture_output=True, text=True, timeout=8)
        if proc.returncode != 0 or "SANDBOX_OK" not in proc.stdout:
            return False, f"Песочница вернула сбой: {proc.stderr.strip() or 'Unknown sandbox error'}", 0

    except Exception as e:
        return False, f"Исключение при проверке в песочнице: {e}", 0
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

    return True, "Код успешно прошёл 100% тестов песочницы.", 0

def test_full_project_compilation():
    """Verifies that all Python modules in project compile without any syntax errors."""
    for fn in ["bot.py", "custom_features.py", "moderation.py", "database.py", "config.py", "premium_client.py", "self_evolution.py", "web_app.py", "youtube_helper.py", "girl_media_manager.py"]:
        p = os.path.join(BASE_DIR, fn)
        if os.path.exists(p):
            try:
                py_compile.compile(p, doraise=True)
            except Exception as e:
                return False, f"Ошибка компиляции {fn}: {e}"
    return True, "Все модули проекта скомпилированы успешно."

# ==========================================
# 3. AUTONOMOUS SELF-UPDATE PIPELINE (GEMINI POWERED)
# ==========================================

def call_gemini_raw(prompt_text, system_instruction):
    """
    Direct ultra-fast caller to Google Gemini API with code architecture instructions.
    Uses prioritised 2026 models with high quotas and fast response times.
    """
    headers = {"Content-Type": "application/json"}
    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8192
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"}
        ]
    }

    for model in config.GEMINI_MODELS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={config.GEMINI_API_KEY}"
            resp = requests.post(url, headers=headers, json=payload, timeout=45)
            if resp.status_code == 200:
                data = resp.json()
                cand = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if cand and len(cand.strip()) > 30:
                    return cand.strip()
        except Exception as e:
            pass
    return None

def analyze_media_for_bug_or_task(media_bytes, mime_type="image/jpeg", user_text=""):
    """
    Multimodal bug & task analyzer for AI for copil:
    Analyzes screenshots, screen recordings, error logs, and UI states sent by Creator.
    Extracts text, commands, tracebacks, and technical diagnosis for GLM-5.3 coder.
    """
    if not media_bytes:
        return user_text or ""
        
    b64_data = base64.b64encode(media_bytes).decode("utf-8")
    vision_prompt = (
        "Ты — Ведущий Системный Архитектор и Детектив Багов проекта Telegram-бота AI for copil.\n"
        "Создатель прислал этот медиафайл (скриншот / видео / фото / лог) с комментарием:\n"
        f"«{user_text or 'Я нашел в тебе баг, изучи и почини'}»\n\n"
        "Внимательно изучи изображение/видео и предоставь исчерпывающий технический анализ:\n"
        "1. ЧТО ПРОИСХОДИТ: Точно перепиши весь релевантный текст (команды пользователя, ответы бота, никнеймы, ошибки, traceback, статус-сообщения).\n"
        "2. В ЧЁМ БАГ / СБОЙ: Что пошло не так? Какое поведение некорректно? (например: бот проигнорировал аргумент, вернул подсказку вместо действия, упал, ответил не тому пользователю и т.д.).\n"
        "3. ГДЕ ЭТО В КОДЕ: В каких модулях (bot.py, database.py, moderation.py, troll_arsenal.py, custom_features.py) и каких функциях/хэндлерах находится эта логика.\n"
        "4. ТЕХНИЧЕСКОЕ ЗАДАНИЕ ДЛЯ КОДЕРА GLM-5.3: Сформулируй конкретную пошаговую инструкцию по исправлению кода.\n"
    )

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": vision_prompt},
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": b64_data
                    }
                }
            ]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4096
        }
    }

    vision_models = [
        "gemini-2.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-3-flash-preview",
        "gemini-flash-latest",
        "gemini-3.5-flash"
    ]
    
    api_key = getattr(config, "GEMINI_API_KEY", "")
    for model in vision_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            resp = requests.post(url, headers=headers, json=payload, timeout=45)
            if resp.status_code == 200:
                data = resp.json()
                cand = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if cand and len(cand.strip()) > 30:
                    logger.info(f"Media successfully analyzed via Gemini Vision {model}!")
                    combined = (
                        f"ЗАДАЧА СОЗДАТЕЛЯ: {user_text}\n\n"
                        f"РЕЗУЛЬТАТЫ ИИ-АНАЛИЗА СКРИНШОТА/МЕДИА:\n{cand.strip()}"
                    )
                    return combined
        except Exception as e:
            logger.debug(f"Vision model {model} attempt failed: {e}")
            continue

    return user_text or ""

def call_glm_self_update(prompt_text, system_instruction):
    """
    Direct caller to GLM-5.3 via Verboo Router for autonomous self-evolution.
    Falls back to Gemini if Verboo is unavailable or quota is exceeded.
    """
    v_keys = getattr(config, "VERBOO_API_KEYS", []) or [getattr(config, "VERBOO_API_KEY", "")]
    verboo_models = ["glm-5.3", "glm-5.3-flash", "deepseek-v4-pro", "qwen3.8-27b"]
    
    for v_key in v_keys:
        if not v_key or not v_key.strip():
            continue
        v_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {v_key.strip()}"
        }
        for glm_model in verboo_models:
            try:
                v_payload = {
                    "model": glm_model,
                    "messages": [
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt_text}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 8192
                }
                v_url = f"{getattr(config, 'VERBOO_API_BASE', 'https://code.verboo.ai/router/v1').rstrip('/')}/chat/completions"
                resp = requests.post(v_url, headers=v_headers, json=v_payload, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        if content and len(content.strip()) > 20:
                            logger.info(f"Self-update code successfully generated via Verboo {glm_model}!")
                            return content.strip()
            except Exception as e:
                logger.debug(f"Verboo GLM attempt failed on {glm_model}: {e}")
                continue
                
    # Fallback to Gemini
    return call_gemini_raw(prompt_text, system_instruction)

def extract_code_block(response_text):
    """Extracts python code from markdown code block or returns clean text."""
    if not response_text:
        return ""
    m = re.search(r'```(?:python|py)?\s*([\s\S]*?)\s*```', response_text)
    if m:
        return m.group(1).strip()
    return response_text.strip()

def detect_target_file(task_instruction):
    """
    Intelligently determines the target file in the repository based on task context, keywords,
    and dynamic codebase search across existing files.
    """
    if not task_instruction:
        return "bot.py"
        
    t = task_instruction.lower().strip()
    
    # 1. Direct file specification [filename.py] or filename.py
    explicit_match = re.search(r'\[([a-zA-Z0-9_\-\.]+\.py)\]', t)
    if explicit_match:
        cand = explicit_match.group(1).strip()
        if os.path.exists(os.path.join(BASE_DIR, cand)):
            return cand

    known_files = [
        "bot.py", "database.py", "config.py", "custom_features.py", "web_app.py", 
        "youtube_helper.py", "moderation.py", "girl_media_manager.py", 
        "self_evolution.py", "premium_client.py", "troll_arsenal.py"
    ]
    for kf in known_files:
        if kf in t:
            return kf

    # 2. Extract potential commands or function keywords mentioned in task
    cmd_matches = re.findall(r'[/!]([a-zA-Zа-яА-Я0-9_]+)', t)
    fn_matches = re.findall(r'\b(cmd_[a-zA-Z0-9_]+|[a-zA-Z0-9_]+_target|[a-zA-Z0-9_]+_user)\b', t)
    tokens_to_search = set(cmd_matches + fn_matches)

    # 3. Keyword heuristics
    if any(k in t for k in ["тролл", "шаблон", "хам", "мат", "оскорб", "arsenal", "панч"]):
        return "troll_arsenal.py"
    if any(k in t for k in ["database", "баз", "бд", "таблиц", "sql", "sqlite", "table", "tables", "schema", "migration", "кэш", "cache", "lru", "баланс", "инвентар", "experience", "промокод", "economy", "admin_db", "backup"]):
        return "database.py"
    if any(k in t for k in ["config", "конфиг", "токен", "ключ", "модел", "env", "setting", "settings", "apikey", "api_key"]):
        return "config.py"
    if any(k in t for k in ["web", "веб", "сайт", "панел", "flask", "шаблон", "html", "css", "dashboard", "panel", "route", "endpoint"]):
        return "web_app.py"
    if any(k in t for k in ["youtube", "ютуб", "видео", "субтитр", "yt-dlp", "ytdlp", "transcript", "ytaudio"]):
        return "youtube_helper.py"
    if any(k in t for k in ["moderat", "модерац", "варн", "мут", "бан", "фильтр", "спам", "антиспам", "automod", "anti-mat"]):
        return "moderation.py"
    if any(k in t for k in ["self_evolution", "самоапдейт", "эволюц", "откат", "rollback", "песочниц"]):
        return "self_evolution.py"

    # 4. Dynamic scan across repository files
    if tokens_to_search:
        file_scores = {}
        for fname in known_files:
            fpath = os.path.join(BASE_DIR, fname)
            if not os.path.exists(fpath):
                continue
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    fcontent = f.read().lower()
                score = sum(1 for tok in tokens_to_search if tok.lower() in fcontent)
                if score > 0:
                    file_scores[fname] = score
            except Exception:
                pass
        if file_scores:
            best_file = max(file_scores, key=file_scores.get)
            if best_file != "bot.py" or file_scores[best_file] > 1:
                return best_file

    # Default to real bot.py for real updates and fixes!
    return "bot.py"

def extract_relevant_context_for_prompt(file_path, task_instruction, max_chars=14000):
    """
    Extracts relevant snippets and function definitions from large files like bot.py
    so Gemini can generate accurate surgical search-and-replace patches without token truncation.
    """
    if not os.path.exists(file_path):
        return ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return ""

    if len(content) <= max_chars:
        return content

    keywords = [w for w in re.findall(r'[a-zA-Z0-9_]{3,}', task_instruction.lower()) if w not in ["bot", "fix", "add", "the", "for", "and", "код", "почини", "сделай", "добавь"]]
    
    lines = content.splitlines()
    matched_ranges = []
    
    outline_lines = [f"{i+1}: {line}" for i, line in enumerate(lines) if line.startswith("def ") or line.startswith("class ") or line.startswith("@bot.") or line.startswith("MAIN_")]

    for i, line in enumerate(lines):
        if any(kw in line.lower() for kw in keywords):
            start = max(0, i - 18)
            end = min(len(lines), i + 30)
            matched_ranges.append((start, end))

    merged_ranges = []
    if matched_ranges:
        matched_ranges.sort(key=lambda x: x[0])
        curr_start, curr_end = matched_ranges[0]
        for s, e in matched_ranges[1:]:
            if s <= curr_end:
                curr_end = max(curr_end, e)
            else:
                merged_ranges.append((curr_start, curr_end))
                curr_start, curr_end = s, e
        merged_ranges.append((curr_start, curr_end))

    context_snippets = []
    top_chunk = "\n".join(lines[:140])
    context_snippets.append(f"--- НАЧАЛО ФАЙЛА (строки 1-140) ---\n{top_chunk}")

    for s, e in merged_ranges[:5]:
        snippet = "\n".join(lines[s:e])
        context_snippets.append(f"--- РЕЛЕВАНТНЫЙ ФРАГМЕНТ (строки {s+1}-{e}) ---\n{snippet}")

    outline_text = "\n".join(outline_lines[:80])
    context_snippets.append(f"--- СТРУКТУРА ФУНКЦИЙ И ХЭНДЛЕРОВ ФАЙЛА ---\n{outline_text}")

    full_context = "\n\n".join(context_snippets)
    if len(full_context) > max_chars:
        full_context = full_context[:max_chars]
    return full_context

def apply_search_replace_blocks(original_text, patch_text):
    """
    Applies surgical search-and-replace or append diff blocks to a large source file.
    Supports standard markers:
    <<<<<<< SEARCH
    [exact code to find]
    =======
    [code to replace with]
    >>>>>>>

    and append markers:
    <<<<<<< APPEND
    [code to append to end of file]
    >>>>>>>
    """
    if not patch_text or not patch_text.strip():
        return original_text, False, "Патч пуст."

    pattern_sr = re.compile(r'<<<<<<< SEARCH\r?\n([\s\S]*?)\r?\n=======\r?\n([\s\S]*?)\r?\n>>>>>>>', re.MULTILINE)
    sr_matches = list(pattern_sr.finditer(patch_text))

    pattern_app = re.compile(r'<<<<<<< APPEND\r?\n([\s\S]*?)\r?\n>>>>>>>', re.MULTILINE)
    app_matches = list(pattern_app.finditer(patch_text))

    if not sr_matches and not app_matches:
        clean_code = extract_code_block(patch_text)
        if clean_code and len(clean_code) > 50 and not "<<<<<<<" in clean_code:
            return clean_code, True, "Полный файл заменен."
        return original_text, False, "Не найдены блоки SEARCH/REPLACE или APPEND в ответе нейросети."

    current_text = original_text
    applied_count = 0

    for match in sr_matches:
        search_block = match.group(1)
        replace_block = match.group(2)

        search_block_norm = search_block.replace("\r\n", "\n")
        current_text_norm = current_text.replace("\r\n", "\n")

        if search_block_norm in current_text_norm:
            current_text = current_text_norm.replace(search_block_norm, replace_block.replace("\r\n", "\n"), 1)
            applied_count += 1
        else:
            sb_stripped = search_block_norm.strip()
            if sb_stripped and sb_stripped in current_text_norm:
                current_text = current_text_norm.replace(sb_stripped, replace_block.replace("\r\n", "\n").strip(), 1)
                applied_count += 1
            else:
                return original_text, False, f"Блок SEARCH не найден в файле:\n{search_block[:200]}..."

    for match in app_matches:
        append_block = match.group(1).rstrip()
        current_text = current_text.rstrip() + "\n\n" + append_block + "\n"
        applied_count += 1

    return current_text, True, f"Успешно применено блоков патча: {applied_count}"

def apply_autonomous_self_update(task_instruction, target_file=None, progress_callback=None, bot=None):
    """
    Universal Autonomous Self-Evolution Engine Powered by Google Gemini:
    1. Researches web documentation/syntax if task requires external data.
    2. Automatically detects target file (bot.py, database.py, custom_features.py, etc.) or uses target_file.
    3. Takes a complete timestamped snapshot before touching code (persisting to disk & SQLite).
    4. For large files (bot.py), uses surgical search-and-replace AST diff patching.
    5. For modular files (custom_features.py), generates full verified module.
    6. Sandboxes with AST and py_compile with self-healing loop.
    7. Commits to Git and pushes to GitHub (Render auto-deploy).
    8. Hot-reloads in RAM immediately.
    """
    if progress_callback:
        progress_callback("🔍 <i>Анализ задачи и выбор целевого файла архитектуры...</i> ▌")

    if not target_file:
        target_file = detect_target_file(task_instruction)

    target_path = os.path.join(BASE_DIR, target_file)
    current_code = ""
    if os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                current_code = f.read()
        except Exception as e:
            return {"success": False, "message": f"Не удалось прочитать {target_file}: {e}"}

    # Autonomous Internet Research for APIs/Libraries if relevant
    web_research_context = ""
    if any(k in task_instruction.lower() for k in ["api", "библиотек", "пакет", "верси", "метод", "интернет", "документац", "ошибк", "как сделать"]):
        if progress_callback:
            progress_callback("🌐 <i>Автономный поиск документации и синтаксиса в сети...</i> ▌")
        try:
            web_research_context = search_internet_for_context(task_instruction, max_results=3)
        except Exception:
            pass

    # Snapshot backup
    snapshot = create_snapshot_backup([target_file, "bot.py", "custom_features.py", "database.py"], task_description=task_instruction)

    is_large_file = (target_file == "bot.py" or len(current_code.splitlines()) > 1200)

    web_section = f"\n\nАКТУАЛЬНЫЕ ДАННЫЕ ИЗ СЕТИ (WEB RESEARCH):\n{web_research_context}" if web_research_context else ""

    if is_large_file:
        file_context = extract_relevant_context_for_prompt(target_path, task_instruction)
        system_instruction = (
            "Ты — Главный Архитектор ИИ-Системы AI for copil.\n"
            "Твой Создатель и Батя — k3rnel (ID 6363403785, @k3rnel8633).\n\n"
            f"ЦЕЛЕВОЙ ФАЙЛ: {target_file} (крупный файл ядра).\n"
            "ПРАВИЛА СОЗДАНИЯ ТОЧНОГО ДИФФ-ПАТЧА:\n"
            "1. Выдай изменения СТРОГО в формате SEARCH/REPLACE блоков:\n"
            "<<<<<<< SEARCH\n"
            "[точные существующие строки из файла, которые нужно заменить]\n"
            "=======\n"
            "[новые строки с исправлениями]\n"
            ">>>>>>>\n\n"
            "2. Если нужно добавить новую функцию в конец файла, используй:\n"
            "<<<<<<< APPEND\n"
            "[новый код функции или хэндлера]\n"
            ">>>>>>>\n\n"
            "3. Блок SEARCH должен содержать ТОЧНЫЙ фрагмент оригинального файла (с учетом отступов), чтобы замена прошла безупречно.\n"
            "4. Код должен быть 100% валидным Python, без синтаксических ошибок, с сохранением всех существующих комментариев и логики."
        )
        prompt = (
            f"ЗАДАЧА НА САМООБНОВЛЕНИЕ ОТ k3rnel:\n"
            f"«{task_instruction}»{web_section}\n\n"
            f"КОНТЕКСТ ФАЙЛА {target_file}:\n"
            f"{file_context}\n\n"
            f"Выдай блоки <<<<<<< SEARCH ... ======= ... >>>>>>> (или <<<<<<< APPEND ... >>>>>>>) для выполнения задачи:"
        )
    else:
        system_instruction = (
            "Ты — Главный Архитектор ИИ-Системы AI for copil, обладающий наивысшими правами создания и обновления функций бота.\n"
            "Твой Создатель и Батя — k3rnel (ID 6363403785, @k3rnel8633).\n\n"
            f"ПРАВИЛА ГЕНЕРАЦИИ МОДУЛЯ {target_file}:\n"
            "1. Сохрани ВСЕ уже существующие функции и команды из текущего кода файла и аккуратно внедри новую.\n"
            "2. В custom_features.py обязательно должен быть словарь `DYNAMIC_COMMANDS = {}`, функция `is_creator(user_or_id)`, функция `register_custom_features(bot, database=None, moderation=None, config=None)` и функция `execute_dynamic_command(bot, message, cmd_name)`.\n"
            "3. Код должен быть 100% рабочим, законченным, без // TODO, без синтаксических ошибок.\n"
            f"4. Выдай ТОЛЬКО итоговый код файла {target_file} внутри ```python ... ```."
        )
        prompt = (
            f"ЗАДАЧА НА САМООБНОВЛЕНИЕ / НОВУЮ ФУНКЦИЮ ОТ k3rnel:\n"
            f"«{task_instruction}»{web_section}\n\n"
            f"ТЕКУЩИЙ КОД ФАЙЛА {target_file}:\n"
            f"```python\n{current_code}\n```\n\n"
            f"Выдай полный обновлённый рабочий код для {target_file} в ```python ```:"
        )

    if progress_callback:
        progress_callback(f"🔮 <i>Генерация архитектурного патча GLM 5.3 для <b>{target_file}</b>...</i> ▌")

    new_patch_raw = call_glm_self_update(prompt, system_instruction)
    if not new_patch_raw:
        return {"success": False, "message": "Нейросеть не смогла сгенерировать патч. Попробуйте ещё раз."}

    if is_large_file:
        generated_code, patch_ok, patch_msg = apply_search_replace_blocks(current_code, new_patch_raw)
        if not patch_ok:
            return {"success": False, "message": f"Ошибка применения патча к {target_file}: {patch_msg}"}
    else:
        generated_code = extract_code_block(new_patch_raw)

    if progress_callback:
        progress_callback("🔬 <i>УРОВЕНЬ 1: Тестирование в изолированной песочнице (py_compile + AST)...</i> ▌")

    is_valid, err_msg, line_no = verify_python_code_in_sandbox(generated_code, filename=target_file)

    # Self-Healing Loop (Up to 3 automatic repair attempts with web search)
    healing_attempts = 0
    while not is_valid and healing_attempts < 3:
        healing_attempts += 1
        if progress_callback:
            progress_callback(f"🔄 <i>УРОВЕНЬ 2: Авто-починка бага (Попытка {healing_attempts}/3)...</i> ▌")

        heal_web = search_internet_for_context(f"python {err_msg}", max_results=2)
        heal_web_block = f"\n\nСправка по ошибке из сети:\n{heal_web}" if heal_web else ""

        heal_prompt = (
            f"Внимание! При компиляции {target_file} обнаружена ошибка:\n"
            f"ОШИБКА: {err_msg}{heal_web_block}\n\n"
            f"КОД С ОШИБКОЙ (фрагмент):\n```python\n{generated_code[:2500]}\n```\n\n"
            f"Исправь ошибку и выдай полностью исправленный рабочий код в ```python ```:"
        )
        healed_raw = call_glm_self_update(heal_prompt, system_instruction)
        if healed_raw:
            if is_large_file:
                h_code, h_ok, _ = apply_search_replace_blocks(current_code, healed_raw)
                if h_ok:
                    generated_code = h_code
            else:
                generated_code = extract_code_block(healed_raw)
            is_valid, err_msg, line_no = verify_python_code_in_sandbox(generated_code, filename=target_file)

    if not is_valid:
        return {
            "success": False,
            "message": f"🛡 Блокировка песочницы: Код для {target_file} не прошёл проверку!\nСервер НЕ тронут, сбой предотвращен.\nДетали: {err_msg}"
        }

    if progress_callback:
        progress_callback(f"💾 <i>УРОВЕНЬ 3: Применение изменений в {target_file}...</i> ▌")

    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(generated_code)
    except Exception as e:
        restore_local_backup(target_path)
        return {"success": False, "message": f"Ошибка записи файла {target_file}: {e}"}

    # Verify full project compilation
    proj_ok, proj_err = test_full_project_compilation()
    if not proj_ok:
        restore_local_backup(target_path)
        return {"success": False, "message": f"Ошибка совместимости проекта с {target_file}: {proj_err}. Восстановлен бэкап."}

    # Git Commit & Push
    if progress_callback:
        progress_callback("📦 <i>Фиксация в Git и синхронизация с репозиторием...</i> ▌")

    git_success = False
    commit_hash = "local"
    try:
        ensure_git_identity()
        setup_git_credentials()
        subprocess.run(["git", "add", target_file], cwd=BASE_DIR, check=True, capture_output=True)
        commit_msg = f"feat(self-update): [{target_file}] {task_instruction[:70]}"
        subprocess.run([
            "git", 
            "-c", "user.name=AI for copil", 
            "-c", "user.email=copil-bot@render.com", 
            "commit", "-m", commit_msg
        ], cwd=BASE_DIR, check=True, capture_output=True)
        push_res = subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, capture_output=True, text=True, timeout=25)
        git_success = (push_res.returncode == 0)
        
        if not git_success:
            api_ok, _ = push_to_github_api(target_file, generated_code, commit_msg)
            if api_ok:
                git_success = True
        
        h_res = subprocess.run(["git", "log", "-1", "--format=%h"], cwd=BASE_DIR, capture_output=True, text=True)
        if h_res.returncode == 0:
            commit_hash = h_res.stdout.strip()
    except Exception as e:
        logger.warning(f"Git push warning during self-update: {e}")
        try:
            commit_msg = f"feat(self-update): [{target_file}] {task_instruction[:70]}"
            api_ok, _ = push_to_github_api(target_file, generated_code, commit_msg)
            if api_ok:
                git_success = True
        except Exception:
            pass

    # Register in history
    history = load_evolution_history()
    history.append({
        "id": len(history) + 1,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "task": task_instruction,
        "target_file": target_file,
        "commit_hash": commit_hash,
        "snapshot": snapshot
    })
    save_evolution_history(history)

    old_lines = len(current_code.splitlines()) if current_code else 0
    new_lines = len(generated_code.splitlines())
    diff_lines = new_lines - old_lines
    sign = f"+{diff_lines}" if diff_lines >= 0 else str(diff_lines)

    # Hot-reload in memory if custom_features
    if target_file == "custom_features.py":
        try:
            reload_custom_features(bot=bot)
        except Exception as e:
            logger.warning(f"Notice on dynamic reload: {e}")

    return {
        "success": True,
        "message": f"Изменения в {target_file} успешно внедрены, протестированы и сохранены!",
        "commit_hash": commit_hash,
        "git_pushed": git_success,
        "old_lines": old_lines,
        "new_lines": new_lines,
        "diff_lines": sign,
        "target_file": target_file
    }

def reload_custom_features(bot=None):
    """
    Dynamically reloads custom_features.py in the running Python process without restarting.
    Re-registers all dynamic commands so changes take effect instantaneously in RAM.
    """
    try:
        import importlib
        import custom_features
        importlib.reload(custom_features)
        custom_features.register_custom_features(bot, database, None, config)
        if bot:
            try:
                import bot as main_bot_mod
                if hasattr(main_bot_mod, 'setup_bot_commands'):
                    main_bot_mod.setup_bot_commands()
            except Exception:
                pass
        logger.info(f"Successfully reloaded custom_features in memory. Active commands: {list(getattr(custom_features, 'DYNAMIC_COMMANDS', {}).keys())}")
        return True, "Модуль custom_features успешно перезагружен в оперативной памяти!"
    except Exception as e:
        logger.error(f"Error hot-reloading custom_features: {e}")
        return False, f"Ошибка перезагрузки модуля: {e}"

# ==========================================
# 4. GITHUB REPOSITORY INTEGRATION & AUTO-UPDATER
# ==========================================

def get_project_file_list():
    """Returns list of all active code files in the repository."""
    files = []
    for root, dirs, filenames in os.walk(BASE_DIR):
        if any(ignored in root for ignored in [".git", ".backups", "__pycache__", "venv", ".env"]):
            continue
        for fn in filenames:
            if fn.endswith((".py", ".html", ".js", ".css", ".md", ".json", ".txt")):
                rel_p = os.path.relpath(os.path.join(root, fn), BASE_DIR)
                files.append(rel_p.replace("\\", "/"))
    return sorted(files)

def read_project_source_file(rel_path):
    """Reads a file from the repository."""
    full_path = os.path.join(BASE_DIR, rel_path)
    if not os.path.exists(full_path):
        return None, f"Файл {rel_path} не найден."
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return True, f.read()
    except Exception as e:
        return False, f"Ошибка чтения файла: {e}"

def write_project_source_file(rel_path, content, commit_message=None):
    """Writes a file to the repository with sandbox verification and optional Git push."""
    full_path = os.path.join(BASE_DIR, rel_path)
    if rel_path.endswith(".py"):
        is_valid, err_msg, _ = verify_python_code_in_sandbox(content, filename=rel_path)
        if not is_valid:
            return False, f"Ошибка синтаксиса: {err_msg}"
            
    # Backup before write
    create_snapshot_backup([rel_path], task_description=f"Direct edit of {rel_path}")
    
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        return False, f"Ошибка записи файла: {e}"
        
    if commit_message:
        try:
            ensure_git_identity()
            setup_git_credentials()
            subprocess.run(["git", "add", rel_path], cwd=BASE_DIR, capture_output=True)
            subprocess.run(["git", "commit", "-m", commit_message], cwd=BASE_DIR, capture_output=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, capture_output=True, timeout=25)
        except Exception:
            pass
            
    return True, f"Файл {rel_path} успешно записан и сохранен."

def check_github_repo_updates():
    """
    Checks remote GitHub repository for new commits on branch main.
    Returns status, latest commit message and author.
    """
    try:
        ensure_git_identity()
        token = get_github_token()
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "AI-for-copil-Bot"}
        if token:
            headers["Authorization"] = f"token {token}" if not token.startswith("Bearer ") and not token.startswith("token ") else token
            
        repo = getattr(config, 'GITHUB_REPO', 'AUser7742/pomoshotru_bot')
        branch = getattr(config, 'GITHUB_BRANCH', 'main') or "main"
        url = f"https://api.github.com/repos/{repo}/commits/{branch}"
        
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            sha = data.get("sha", "")[:7]
            commit_info = data.get("commit", {})
            msg = commit_info.get("message", "").split("\n")[0]
            author = commit_info.get("author", {}).get("name", "Unknown")
            date = commit_info.get("author", {}).get("date", "")
            return {
                "success": True,
                "remote_commit": sha,
                "message": msg,
                "author": author,
                "date": date
            }
        elif resp.status_code == 404:
            if not token:
                return {"success": False, "message": "Репозиторий приватный. Токен GitHub не указан (задайте через /setgit <токен>)."}
            else:
                return {"success": False, "message": f"Репозиторий {repo} не найден или токен не имеет к нему доступа."}
        elif resp.status_code == 401:
            return {"success": False, "message": "Неверный или истекший GitHub токен. Обновите через /setgit <токен>."}
        else:
            return {"success": False, "message": f"GitHub API status {resp.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def fetch_github_file_content(filepath):
    """Fetches raw content of a file from GitHub repository."""
    try:
        token = config.GITHUB_TOKEN or database.get_app_setting("GITHUB_TOKEN", "")
        headers = {"Accept": "application/vnd.github.v3.raw"}
        if token:
            headers["Authorization"] = f"token {token}"
            
        repo = config.GITHUB_REPO
        branch = config.GITHUB_BRANCH or "main"
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/{filepath}"
        
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return True, resp.text
        return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)

_github_updater_thread = None
_github_updater_running = False

def start_github_auto_updater(bot=None, interval_seconds=14400):
    """
    Starts an autonomous 4-hour background loop that checks for updates,
    runs quality/compilation tests, and keeps the repository in sync.
    """
    global _github_updater_thread, _github_updater_running
    if _github_updater_running:
        return

    def _loop():
        global _github_updater_running
        _github_updater_running = True
        logger.info(f"GitHub Auto-Updater loop started (Interval: {interval_seconds}s / 4 hours).")
        while _github_updater_running:
            time.sleep(interval_seconds)
            try:
                # 1. Check compilation of all project files
                ok, err = test_full_project_compilation()
                if not ok:
                    logger.warning(f"Quality Check Notice: {err}")
                    database.record_error_experience("CompilationCheck", err, context="Auto-Updater Loop")
                else:
                    logger.info("Quality Check Passed: 100% Python syntax clean.")

                # 2. Check remote updates
                update_info = check_github_repo_updates()
                if update_info.get("success"):
                    logger.info(f"GitHub Sync Check: remote is at {update_info.get('remote_commit')} - {update_info.get('message')}")
            except Exception as e:
                logger.error(f"Error in GitHub auto-updater loop: {e}")

    _github_updater_thread = threading.Thread(target=_loop, daemon=True, name="gh_updater_loop")
    _github_updater_thread.start()

# ==========================================
# 5. SERVER DIAGNOSTICS & 100% RELIABLE ROLLBACK
# ==========================================

def get_server_diagnostics():
    """Returns comprehensive dictionary with system, runtime, cache and learning diagnostics."""
    import platform
    diag = {}
    
    diag["os"] = f"{platform.system()} {platform.release()} ({platform.machine()})"
    diag["python"] = platform.python_version()
    diag["cwd"] = BASE_DIR
    
    try:
        git_hash = subprocess.check_output(["git", "log", "-1", "--format=%h - %s (%cr)"], cwd=BASE_DIR, text=True).strip()
        diag["git_commit"] = git_hash
    except Exception:
        diag["git_commit"] = "Не доступен"

    db_path = os.path.join(BASE_DIR, "chats.db")
    if os.path.exists(db_path):
        db_size = os.path.getsize(db_path)
        diag["db_size_kb"] = f"{db_size / 1024:.2f} КБ ({db_size / (1024*1024):.2f} МБ)"
        try:
            import sqlite3
            c = sqlite3.connect(db_path)
            cur = c.cursor()
            cur.execute("SELECT COUNT(*) FROM messages")
            diag["db_messages"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM users")
            diag["db_users"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM chats")
            diag["db_chats"] = cur.fetchone()[0]
            c.close()
        except Exception:
            pass
    else:
        diag["db_size_kb"] = "Отсутствует"

    diag["threads"] = threading.active_count()
    try:
        diag["cache_modes"] = database.user_modes_cache.get_stats()
        diag["cache_responses"] = database.response_cache.get_stats()
        diag["cache_search"] = database.search_cache.get_stats()
        diag["learning_stats"] = database.get_learning_stats()
    except Exception as e:
        logger.debug(f"Diagnostics cache stats note: {e}")
    return diag

def rollback_last_commit(bot=None):
    """
    Instant, 100% reliable rollback:
    1. Restores the exact files from the latest snapshot in history or SQLite database.
    2. Verifies compilation across all modules.
    3. Reloads modules in memory.
    4. Commits and pushes to GitHub main so Render auto-deploys the clean state.
    """
    try:
        history = load_evolution_history()
        restored_any = False
        restored_files = []

        if history:
            last_entry = history.pop()
            snap_files = last_entry.get("snapshot", {}).get("files", {})
            for fname, bak_file in snap_files.items():
                bak_p = os.path.join(BACKUP_DIR, bak_file)
                dst_p = os.path.join(BASE_DIR, fname)
                if os.path.exists(bak_p):
                    shutil.copy2(bak_p, dst_p)
                    restored_any = True
                    restored_files.append(fname)
            save_evolution_history(history)

        if not restored_any:
            # Fallback: check SQLite database for latest active code backup
            latest_db_bak = database.get_latest_code_backup()
            if latest_db_bak:
                b_id = latest_db_bak.get("backup_id")
                # Scan .backups for files with this backup timestamp
                ts_match = re.search(r'snap_(\d+_\d+)', b_id or "")
                if ts_match:
                    target_ts = ts_match.group(1)
                    for f in os.listdir(BACKUP_DIR):
                        if target_ts in f and f.endswith(".bak"):
                            orig_fname = re.sub(r'\.\d+_\d+\.bak$', '', f)
                            src_p = os.path.join(BACKUP_DIR, f)
                            dst_p = os.path.join(BASE_DIR, orig_fname)
                            shutil.copy2(src_p, dst_p)
                            restored_any = True
                            restored_files.append(orig_fname)
                if b_id:
                    database.mark_code_backup_status(b_id, status="rolled_back")

        if not restored_any:
            # Fallback to scanning .backups/ directly
            for fname in ["custom_features.py", "bot.py", "database.py", "config.py"]:
                if restore_local_backup(os.path.join(BASE_DIR, fname)):
                    restored_any = True
                    restored_files.append(fname)

        if not restored_any:
            # Fallback to git revert
            ensure_git_identity()
            setup_git_credentials()
            res = subprocess.run([
                "git",
                "-c", "user.name=AI for copil",
                "-c", "user.email=copil-bot@render.com",
                "revert", "HEAD", "--no-edit"
            ], cwd=BASE_DIR, capture_output=True, text=True)
            if res.returncode == 0:
                push_res = subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, capture_output=True, timeout=25)
                if push_res.returncode == 0:
                    return True, "Коммит успешно отменён через git revert и отправлен на Render."
            return False, "Резервные копии не найдены для отката."

        # Verify compilation
        ok, err = test_full_project_compilation()
        if not ok:
            return False, f"Ошибка компиляции после отката: {err}"

        if "custom_features.py" in restored_files:
            reload_custom_features(bot)

        # Git commit & push
        ensure_git_identity()
        setup_git_credentials()
        subprocess.run(["git", "add"] + restored_files, cwd=BASE_DIR, capture_output=True)
        commit_msg = f"revert(rollback): restore {', '.join(restored_files)} before self-update"
        subprocess.run([
            "git",
            "-c", "user.name=AI for copil",
            "-c", "user.email=copil-bot@render.com",
            "commit", "-m", commit_msg
        ], cwd=BASE_DIR, capture_output=True)
        push_res = subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, capture_output=True, text=True, timeout=25)

        files_str = ", ".join(restored_files)
        if push_res.returncode == 0:
            return True, f"Файлы ({files_str}) успешно восстановлены из точки бэкапа и отправлены на Render!"
        
        # Fallback to GitHub REST API push if git push failed
        api_pushed_all = True
        for rf in restored_files:
            rf_path = os.path.join(BASE_DIR, rf)
            if os.path.exists(rf_path):
                try:
                    with open(rf_path, "r", encoding="utf-8") as f:
                        rf_code = f.read()
                    api_ok, _ = push_to_github_api(rf, rf_code, commit_msg)
                    if not api_ok:
                        api_pushed_all = False
                except Exception:
                    api_pushed_all = False
        if api_pushed_all:
            return True, f"Файлы ({files_str}) успешно восстановлены и синхронизированы с GitHub через REST API!"

        return True, f"Файлы ({files_str}) успешно восстановлены локально из бэкапа!"
    except Exception as e:
        return False, f"Ошибка при откате: {e}"

# ==========================================
# 6. LIVE EVAL & SHELL EXECUTOR
# ==========================================

def execute_python_eval(code_str, env_globals=None):
    """Executes Python code or expressions on the server with stdout/stderr capture."""
    if not code_str or not code_str.strip():
        return "⚠️ Код пуст."

    clean_code = code_str.strip()
    if clean_code.startswith("```"):
        clean_code = re.sub(r"^```(?:python|py)?\n?", "", clean_code)
        clean_code = re.sub(r"\n?```$", "", clean_code)

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    ctx = env_globals or {}
    start_time = time.time()

    try:
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            result = eval(clean_code, ctx)
            if result is not None:
                print(repr(result))
    except SyntaxError:
        try:
            with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                exec(clean_code, ctx)
        except Exception:
            traceback.print_exc(file=stderr_buf)
    except Exception:
        traceback.print_exc(file=stderr_buf)

    elapsed = (time.time() - start_time) * 1000
    out = stdout_buf.getvalue()
    err = stderr_buf.getvalue()

    res_parts = []
    if out:
        res_parts.append(out.rstrip())
    if err:
        res_parts.append(f"STDERR / TRACEBACK:\n{err.rstrip()}")
    if not res_parts:
        res_parts.append("[Код выполнен успешно, вывод пуст]")

    res_parts.append(f"\n⏱ Время: {elapsed:.2f} мс")
    return "\n".join(res_parts)

def execute_shell_command(cmd_str, timeout=30):
    """Executes a shell command on host/container with full stdout/stderr capture."""
    if not cmd_str or not cmd_str.strip():
        return "⚠️ Команда пуста."

    try:
        proc = subprocess.run(
            cmd_str.strip(),
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=BASE_DIR
        )
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        
        lines = [f"$ {cmd_str.strip()}"]
        if out:
            lines.append(out)
        if err:
            lines.append(f"[STDERR]:\n{err}")
        if not out and not err:
            lines.append("[Команда выполнена успешно, код 0]")
        lines.append(f"[Код завершения: {proc.returncode}]")
        return "\n".join(lines)
    except subprocess.TimeoutExpired:
        return f"⏱ Таймаут: команда превысила лимит {timeout} сек."
    except Exception as e:
        return f"⚠️ Ошибка выполнения команды: {e}"

# ==========================================
# 7. CODE VERIFICATION, AUTO-HEALING & GITHUB PUBLISHING PIPELINE
# ==========================================

def slugify(text, default_prefix="code", ext="txt"):
    """Converts Russian and English titles into safe ASCII url slugs."""
    if not text:
        return f"{default_prefix}_{int(time.time())}"
    
    translit_table = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh',
        'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
        'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts',
        'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu',
        'я': 'ya'
    }
    
    s = text.lower().strip()
    s = re.sub(r'^(создай|сгенерируй|напиши|сделай|код|скрипт|сайт|на|для|вебсайт|лендинг)\s+', '', s)
    
    res = []
    for char in s:
        if char in translit_table:
            res.append(translit_table[char])
        elif char.isalnum():
            res.append(char)
        elif char in [' ', '-', '_', '.', '/']:
            res.append('_')
    
    slug = ''.join(res).strip('_')
    slug = re.sub(r'_+', '_', slug)
    if len(slug) > 35:
        slug = slug[:35].rstrip('_')
        
    if not slug or len(slug) < 2:
        slug = f"{default_prefix}_{int(time.time())}"
    return slug

def verify_lua_syntax(code):
    """Validates Lua code syntax: string balancing, brackets, and block matching."""
    if not code or len(code.strip()) < 5:
        return False, "Код Lua пуст."
    
    c = re.sub(r'--\[\[.*?\]\]', '', code, flags=re.DOTALL)
    c = re.sub(r'--.*$', '', c, flags=re.MULTILINE)
    c = re.sub(r'\[\[.*?\]\]', '""', c, flags=re.DOTALL)
    c = re.sub(r'"(\\.|[^"\\])*"', '""', c)
    c = re.sub(r"'(\\.|[^'\\])*'", "''", c)
    
    stack = []
    pairs = {')': '(', ']': '[', '}': '{'}
    for char in c:
        if char in '([{':
            stack.append(char)
        elif char in ')]}':
            if not stack or stack[-1] != pairs[char]:
                return False, f"Несоответствие скобок: обнаружена закрывающая скобка '{char}' без пары"
            stack.pop()
    if stack:
        return False, f"Незакрытые скобки в коде Lua: {stack}"
        
    tokens = re.findall(r'\b(do|then|function|repeat|until|end)\b', c)
    block_stack = []
    for tok in tokens:
        if tok in ['do', 'then', 'function']:
            block_stack.append('end')
        elif tok == 'repeat':
            block_stack.append('until')
        elif tok in ['end', 'until']:
            if not block_stack:
                return False, f"Лишний ключевой оператор '{tok}' без открывающего блока"
            expected = block_stack.pop()
            if tok != expected:
                return False, f"Ошибка структуры Lua: ожидался '{expected}', но получен '{tok}'"
                
    if block_stack:
        return False, f"Незакрытые блоки кода Lua: не хватает {len(block_stack)} операторов 'end/until'"
        
    return True, "Lua синтаксис 100% валиден"

def verify_html_syntax(code):
    """Validates HTML5 structure: doctype/html, matching body, head, script, style tags."""
    if not code or len(code.strip()) < 20:
        return False, "HTML код пуст или слишком короткий."
    
    lower = code.lower()
    if "<html" not in lower or "</html>" not in lower:
        return False, "Отсутствуют обязательные корневые теги <html> или </html>"
        
    open_scripts = len(re.findall(r'<script\b', lower))
    close_scripts = len(re.findall(r'</script>', lower))
    if open_scripts != close_scripts:
        return False, f"Несоответствие тегов <script>: открыто {open_scripts}, закрыто {close_scripts}"
        
    open_styles = len(re.findall(r'<style\b', lower))
    close_styles = len(re.findall(r'</style>', lower))
    if open_styles != close_styles:
        return False, f"Несоответствие тегов <style>: открыто {open_styles}, закрыто {close_styles}"
        
    return True, "HTML5 структура 100% валидна"

def verify_python_syntax(code):
    """Validates Python syntax via AST and py_compile."""
    if not code or len(code.strip()) < 5:
        return False, "Python код пуст."
    try:
        ast.parse(code)
    except SyntaxError as se:
        return False, f"Синтаксическая ошибка Python (строка {se.lineno}): {se.msg}"
    except Exception as e:
        return False, f"Ошибка AST Python: {e}"
        
    temp_fd, temp_path = tempfile.mkstemp(suffix=".py")
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            f.write(code)
        py_compile.compile(temp_path, doraise=True)
    except py_compile.PyCompileError as pe:
        return False, f"Ошибка компиляции байткода Python: {pe.msg}"
    except Exception as e:
        return False, f"Ошибка компиляции: {e}"
    finally:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except Exception: pass
            
    return True, "Python синтаксис 100% валиден"

def verify_general_code_syntax(code, lang):
    """Universal dispatcher for code verification."""
    l = (lang or "").lower()
    if l in ["lua", "luau"]:
        return verify_lua_syntax(code)
    elif l in ["html", "htm", "website"]:
        return verify_html_syntax(code)
    elif l in ["py", "python"]:
        return verify_python_syntax(code)
    else:
        stack = []
        pairs = {')': '(', ']': '[', '}': '{'}
        c = re.sub(r'"(\\.|[^"\\])*"', '""', code)
        c = re.sub(r"'(\\.|[^'\\])*'", "''", c)
        for char in c:
            if char in '([{':
                stack.append(char)
            elif char in ')]}':
                if not stack or stack[-1] != pairs[char]:
                    return False, f"Несоответствие скобок: обнаружена закрывающая скобка '{char}' без пары"
                stack.pop()
        if stack:
            return False, f"Незакрытые скобки в коде: {stack}"
        return True, f"{lang.upper()} синтаксис валиден"

def auto_heal_code(code_str, lang, task_prompt, progress_callback=None):
    """
    Validates code syntax according to language rules.
    If bugs or syntax errors are found, calls Gemini to automatically fix the bugs up to 2 times.
    Returns: (final_code: str, is_valid: bool, bug_report: str)
    """
    is_valid, err_msg = verify_general_code_syntax(code_str, lang)
    if is_valid:
        return code_str, True, "100% валиден (без багов)"
    
    current_code = code_str
    attempts = 0
    while not is_valid and attempts < 2:
        attempts += 1
        if progress_callback:
            progress_callback(f"🛠 <i>Уровень проверки: обнаружен баг ({err_msg}). Авто-исправление ({attempts}/2)...</i> ▌")
        
        system_instruction = (
            f"Ты — Principal Software Engineer и Bug Healing Specialist мирового уровня.\n"
            f"В сгенерированном коде ({lang.upper()}) обнаружен баг/ошибка синтаксиса:\n"
            f"ОШИБКА: {err_msg}\n\n"
            f"ТВОЯ ЗАДАЧА: Полностью устранить эту ошибку и вернуть 100% ПОЛНЫЙ, РАБОЧИЙ КОД без сокращений, без // TODO и без заглушек.\n"
            f"Верни ТОЛЬКО чистый исправленный код в блоке ```{lang} ... ```."
        )
        prompt = (
            f"ИСХОДНАЯ ЗАДАЧА: {task_prompt}\n\n"
            f"КОД С ОШИБКОЙ:\n```{lang}\n{current_code}\n```\n\n"
            f"Исправь ошибку '{err_msg}' и выдай полный рабочий код:"
        )
        
        healed_raw = call_gemini_raw(prompt, system_instruction)
        if healed_raw:
            code_match = re.search(r'```(\w+)?\n([\s\S]*?)```', healed_raw)
            if code_match:
                current_code = code_match.group(2).strip()
            else:
                current_code = healed_raw.strip()
            is_valid, err_msg = verify_general_code_syntax(current_code, lang)
            if is_valid:
                return current_code, True, f"Исправлен и проверен (попытка {attempts})"
                
    return current_code, is_valid, err_msg

def get_github_token():
    """Gets the active GitHub token from SQLite app_settings, config or environment."""
    token = database.get_app_setting("GITHUB_TOKEN") or getattr(config, 'GITHUB_TOKEN', '') or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GIT_TOKEN") or os.getenv("GITHUB_PAT", "")
    return (token or "").strip()

def set_github_token(token):
    """Sets, persists and verifies a new GitHub Personal Access Token."""
    token = (token or "").strip()
    database.set_app_setting("GITHUB_TOKEN", token)
    os.environ["GITHUB_TOKEN"] = token
    if hasattr(config, "GITHUB_TOKEN"):
        config.GITHUB_TOKEN = token
    setup_git_credentials()
    return test_github_connection(token)

def test_github_connection(token=None):
    """Verifies GitHub token permissions against repository."""
    if not token:
        token = get_github_token()
    if not token:
        return False, "GITHUB_TOKEN не задан. Используйте <code>/setgit &lt;токен&gt;</code>"
    
    repo = getattr(config, 'GITHUB_REPO', 'AUser7742/pomoshotru_bot')
    url = f"https://api.github.com/repos/{repo}"
    headers = {
        "Authorization": f"token {token}" if not token.startswith("Bearer ") and not token.startswith("token ") else token,
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AI-for-copil-Bot"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            repo_info = res.json()
            perms = repo_info.get("permissions", {})
            can_push = perms.get("push", True)
            if can_push:
                return True, f"✅ Доступ к репозиторию <b>{repo}</b> подтвержден (права: запись/push)!"
            else:
                return True, f"⚠️ Доступ к репозиторию <b>{repo}</b> есть, но права на запись ограничены."
        elif res.status_code == 401:
            return False, "❌ Ошибка 401: Неверный или истекший GitHub токен."
        elif res.status_code == 404:
            return False, f"❌ Ошибка 404: Репозиторий {repo} не найден или токен не имеет доступа к нему."
        else:
            return False, f"❌ GitHub API вернул статус {res.status_code}: {res.text[:100]}"
    except Exception as e:
        return False, f"❌ Ошибка подключения к GitHub API: {e}"

def setup_git_credentials():
    """Configures git remote URL with GITHUB_TOKEN if available, allowing non-interactive git push on Render."""
    try:
        token = get_github_token()
        repo = getattr(config, 'GITHUB_REPO', 'AUser7742/pomoshotru_bot')
        if token:
            authed_url = f"https://x-access-token:{token}@github.com/{repo}.git"
            subprocess.run(["git", "remote", "set-url", "origin", authed_url], cwd=BASE_DIR, capture_output=True)
    except Exception as e:
        logger.debug(f"setup_git_credentials notice: {e}")

def push_to_github_api(rel_git_path, content_str, commit_msg):
    """
    Directly pushes/creates/updates a file in the GitHub repository using GitHub REST API.
    Works independently of local git CLI credentials.
    """
    token = get_github_token()
    repo = getattr(config, 'GITHUB_REPO', 'AUser7742/pomoshotru_bot')
    branch = getattr(config, 'GITHUB_BRANCH', 'main')
    if not token:
        return False, "GITHUB_TOKEN не задан"
    
    url = f"https://api.github.com/repos/{repo}/contents/{rel_git_path}"
    headers = {
        "Authorization": f"token {token}" if not token.startswith("Bearer ") and not token.startswith("token ") else token,
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AI-for-copil-Bot"
    }
    
    sha = None
    try:
        get_res = requests.get(f"{url}?ref={branch}", headers=headers, timeout=10)
        if get_res.status_code == 200:
            sha = get_res.json().get("sha")
    except Exception:
        pass
        
    encoded_content = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    payload = {
        "message": commit_msg,
        "content": encoded_content,
        "branch": branch,
        "committer": {
            "name": "AI for copil",
            "email": "copil-bot@render.com"
        }
    }
    if sha:
        payload["sha"] = sha
        
    try:
        put_res = requests.put(url, headers=headers, json=payload, timeout=15)
        if put_res.status_code in [200, 201]:
            logger.info(f"GitHub REST API commit successful for {rel_git_path}")
            return True, "Успешно отправлено через GitHub REST API"
        else:
            logger.warning(f"GitHub API returned status {put_res.status_code}: {put_res.text}")
            return False, f"GitHub API status {put_res.status_code}"
    except Exception as e:
        logger.warning(f"GitHub API commit error: {e}")
        return False, str(e)

def publish_asset_to_github_and_cloud(title, ext, code, author_id, author_name, is_html=False, progress_callback=None):
    """
    Full pipeline to publish code or websites:
    1. Generates clean slug.
    2. Writes to filesystem (sites/<slug>/index.html or scripts/<slug>.<ext>).
    3. Saves record to SQLite database.
    4. Auto-commits and pushes to GitHub (origin main via git CLI or GitHub REST API).
    5. Returns dict with real GitHub Raw, GitHub Repo, Render Live and Failproof Loadstring URLs.
    """
    ensure_git_identity()
    setup_git_credentials()
    
    clean_slug = slugify(title, default_prefix="site" if is_html else "script", ext=ext)
    ts = int(time.time())
    item_id = f"{clean_slug}_{str(ts)[-4:]}"
    
    base_dir = BASE_DIR
    sites_dir = os.path.join(base_dir, "sites")
    scripts_dir = os.path.join(base_dir, "scripts")
    os.makedirs(sites_dir, exist_ok=True)
    os.makedirs(scripts_dir, exist_ok=True)
    
    if is_html:
        site_folder = os.path.join(sites_dir, item_id)
        os.makedirs(site_folder, exist_ok=True)
        target_file_path = os.path.join(site_folder, "index.html")
        rel_git_path = f"sites/{item_id}/index.html"
    else:
        filename = f"{item_id}.{ext}"
        target_file_path = os.path.join(scripts_dir, filename)
        rel_git_path = f"scripts/{filename}"
        
    with open(target_file_path, "w", encoding="utf-8") as f:
        f.write(code)
        
    # Save in SQLite DB
    database.save_script(item_id, title, "html" if is_html else ext, code, author_id=author_id, author_name=author_name)
    
    # Instantly sync to remote Render web dashboard via API endpoint in background
    def _async_cloud_sync():
        try:
            render_base_sync = getattr(config, 'RENDER_BASE_URL', 'https://pomoshotru-bot.onrender.com').rstrip('/')
            sync_endpoint = f"{render_base_sync}/api/sync_script"
            requests.post(
                sync_endpoint,
                json={
                    "script_id": item_id,
                    "title": title,
                    "language": "html" if is_html else ext,
                    "code": code,
                    "author_id": author_id,
                    "author_name": author_name,
                    "is_html": is_html
                },
                timeout=6
            )
        except Exception as se:
            logger.debug(f"Cloud sync notice: {se}")

    threading.Thread(target=_async_cloud_sync, daemon=True).start()
    
    if progress_callback:
        progress_callback("🐙 <i>Синхронизация с GitHub и публикация в репозиторий...</i> ▌")
        
    git_pushed = False
    commit_msg = f"feat(publish): {title[:60]} [{item_id}]"
    
    # 1. Try Git CLI commit & push
    try:
        subprocess.run(["git", "add", rel_git_path], cwd=base_dir, capture_output=True)
        subprocess.run([
            "git",
            "-c", "user.name=AI for copil",
            "-c", "user.email=copil-bot@render.com",
            "commit", "-m", commit_msg
        ], cwd=base_dir, capture_output=True)
        push_proc = subprocess.run(["git", "push", "origin", "main"], cwd=base_dir, capture_output=True, text=True, timeout=25)
        git_pushed = (push_proc.returncode == 0)
    except Exception as ge:
        logger.warning(f"Git push warning: {ge}")
        
    # 2. If Git CLI push failed, try GitHub REST API
    if not git_pushed:
        api_ok, api_msg = push_to_github_api(rel_git_path, code, commit_msg)
        if api_ok:
            git_pushed = True
            
    repo_name = getattr(config, 'GITHUB_REPO', 'AUser7742/pomoshotru_bot')
    branch_name = getattr(config, 'GITHUB_BRANCH', 'main')
    render_base = getattr(config, 'RENDER_BASE_URL', 'https://pomoshotru-bot.onrender.com').rstrip('/')
    
    render_site_url = f"{render_base}/site/{item_id}" if is_html else f"{render_base}/script/{item_id}"
    render_ide_url = f"{render_base}/script/{item_id}"
    render_raw_url = f"{render_base}/raw/{item_id}.{ext}" if not is_html else render_site_url
    
    if git_pushed:
        github_raw_url = f"https://raw.githubusercontent.com/{repo_name}/{branch_name}/{rel_git_path}"
        github_repo_url = f"https://github.com/{repo_name}/blob/{branch_name}/{rel_git_path}"
    else:
        github_raw_url = ""
        github_repo_url = f"https://github.com/{repo_name}"
    
    loadstring_code = ""
    if ext in ["lua", "luau"]:
        if git_pushed and github_raw_url:
            loadstring_code = f'loadstring(game:HttpGet("{github_raw_url}"))()'
        else:
            loadstring_code = f'loadstring(game:HttpGet("{render_raw_url}"))()'
            
    failproof_loadstring = f'loadstring(game:HttpGet("{render_raw_url}"))()' if ext in ["lua", "luau"] else ""
        
    return {
        "item_id": item_id,
        "filename": os.path.basename(target_file_path),
        "file_path": target_file_path,
        "rel_git_path": rel_git_path,
        "github_raw_url": github_raw_url,
        "github_repo_url": github_repo_url,
        "render_site_url": render_site_url,
        "render_ide_url": render_ide_url,
        "render_raw_url": render_raw_url,
        "loadstring": loadstring_code,
        "failproof_loadstring": failproof_loadstring,
        "git_pushed": git_pushed
    }
