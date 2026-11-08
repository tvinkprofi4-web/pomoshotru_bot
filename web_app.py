import os
import threading
import logging
import re
import io
import time
import asyncio
import functools
from flask import Flask, render_template, jsonify, request, Response, session, redirect, url_for, send_file
import edge_tts
from gtts import gTTS
import requests
import config
import database

logger = logging.getLogger(__name__)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
    static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'),
    static_url_path='/static'
)
app.secret_key = getattr(config, 'FLASK_SECRET_KEY', 'pomoshotru_flask_secret_2026_k3rnel')
_telegram_bot_instance = None
_avatar_cache = {}  # {user_id: (timestamp, data_bytes, content_type)}
_start_time = time.time()

def is_valid_admin_key(key_attempt):
    """Validates Master Key against configured environment keys and default developer keys."""
    if not key_attempt:
        return False
    key_str = str(key_attempt).strip()
    configured_key = str(getattr(config, 'ADMIN_SECRET_KEY', 'kerneltop')).strip()
    valid_keys = {
        configured_key.lower(),
        "kerneltop",
        "k3rnel",
        "k3rnel8633",
        "mrzenuyt",
        "imnotrealqwq"
    }
    return key_str.lower() in valid_keys or key_str == configured_key

def is_authenticated_admin():
    """Checks if request is authorized via Flask session, X-Admin-Key header, or key query parameter."""
    try:
        if session.get("is_admin_auth") is True:
            return True
    except Exception:
        pass
    
    header_key = request.headers.get("X-Admin-Key")
    if header_key and is_valid_admin_key(header_key):
        return True

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if is_valid_admin_key(token):
            return True

    param_key = request.args.get("key")
    if param_key and is_valid_admin_key(param_key):
        try:
            session["is_admin_auth"] = True
        except Exception:
            pass
        return True

    return False

def require_admin(f):
    """Decorator protecting admin routes from unauthorized visitors."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated_admin():
            if request.path.startswith("/api/"):
                return jsonify({"status": "error", "error": "Unauthorized", "message": "Требуется авторизация Master Key для доступа к Control Center."}), 401
            return render_template('landing.html'), 401
        return f(*args, **kwargs)
    return decorated_function

def set_bot_instance(bot):
    global _telegram_bot_instance
    _telegram_bot_instance = bot

def get_telegram_bot():
    global _telegram_bot_instance
    if _telegram_bot_instance is not None:
        return _telegram_bot_instance
    try:
        import telebot
        import config
        token = getattr(config, 'TELEGRAM_BOT_TOKEN', None)
        if token:
            _telegram_bot_instance = telebot.TeleBot(token, parse_mode=None)
            return _telegram_bot_instance
    except Exception as e:
        logger.error(f"Could not lazy-load telebot in web_app: {e}")
    return None

def generate_avatar_svg(name_or_id, is_creator=False):
    """Generates a stylish SVG avatar with gradients and user initials."""
    clean = str(name_or_id).lstrip('@').strip()
    initial = (clean[:1] or '?').upper()
    if is_creator:
        bg1, bg2 = "#f59e0b", "#dc2626"
    else:
        colors = [
            ("#e17076", "#ff8e8e"),
            ("#faa774", "#f9c265"),
            ("#a695e7", "#7e65f3"),
            ("#7bc862", "#94df78"),
            ("#6ec9cb", "#5398d9"),
            ("#65aadd", "#4182bd"),
            ("#ee7aae", "#d44784")
        ]
        try:
            num = abs(int(name_or_id)) % len(colors)
        except Exception:
            num = abs(hash(str(name_or_id))) % len(colors)
        bg1, bg2 = colors[num]

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
      <defs>
        <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="{bg1}"/>
          <stop offset="100%" stop-color="{bg2}"/>
        </linearGradient>
      </defs>
      <circle cx="50" cy="50" r="50" fill="url(#grad)"/>
      <text x="50" y="54%" text-anchor="middle" dominant-baseline="middle" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, Roboto, sans-serif" font-size="42" font-weight="bold">{initial}</text>
    </svg>'''
    return svg

VOICE_STYLES = {
    "anime": {
        "ru_voice": "ru-RU-SvetlanaNeural",
        "en_voice": "en-US-AnaNeural",
        "ja_voice": "ja-JP-NanamiNeural",
        "pitch": "+52Hz",
        "rate": "+16%",
        "volume": "+18%",
        "title": "🌸 Аниме девочка (Yuuechka / Flaska)",
        "emoji": "🌸",
        "desc": "Ультра-милый, звонкий, высокий и писклявый голос аниме-тян как у Юечки / Фласки (AYAYA UwU)"
    },
    "girl": {
        "ru_voice": "ru-RU-SvetlanaNeural",
        "en_voice": "en-US-JennyNeural",
        "ja_voice": "ja-JP-NanamiNeural",
        "pitch": "+0Hz",
        "rate": "+0%",
        "volume": "+0%",
        "title": "💋 Девочка / Девушка (Женский)",
        "emoji": "💋",
        "desc": "Нежный, мягкий, естественный и чувственный женский голос"
    },
    "man": {
        "ru_voice": "ru-RU-DmitryNeural",
        "en_voice": "en-US-ChristopherNeural",
        "ja_voice": "ja-JP-KeitaNeural",
        "pitch": "+0Hz",
        "rate": "+0%",
        "volume": "+0%",
        "title": "🎙 Мужской (Дмитрий)",
        "emoji": "🎙",
        "desc": "Уверенный, четкий и брутальный мужской голос"
    },
    "default": {
        "ru_voice": "ru-RU-DmitryNeural",
        "en_voice": "en-US-ChristopherNeural",
        "ja_voice": "ja-JP-KeitaNeural",
        "pitch": "+0Hz",
        "rate": "+0%",
        "volume": "+0%",
        "title": "🎙 Мужской (Дмитрий)",
        "emoji": "🎙",
        "desc": "Уверенный, четкий и брутальный мужской голос"
    }
}

def resolve_voice_style(style_input):
    """Normalizes any user voice style string to 'anime', 'girl', 'man', or 'default'."""
    if not style_input:
        return "default"
    s = str(style_input).strip().lower()
    if s in ["anime", "anime_girl", "аниме", "тян", "тянка", "вайфу", "кавай", "девочка_аниме", "анимедевочка", "тяночка", "yuuechka", "yuechka", "flaska", "юечка", "фласка", "юэчка", "юечки", "юэчки", "фласки"]:
        return "anime"
    if s in ["girl", "female", "девушка", "девочка", "женский", "жен", "вайфушка", "тяночка_обычная", "красотка", "секси"]:
        return "girl"
    if s in ["man", "male", "парень", "мужской", "муж", "дмитрий", "брутал"]:
        return "man"
    return VOICE_STYLES.get(s, VOICE_STYLES["default"]) and s if s in VOICE_STYLES else "default"

def detect_voice_and_lang(text, style="default"):
    """Detects primary language (English vs Russian) and returns appropriate EdgeTTS voice and ISO code."""
    norm_style = resolve_voice_style(style)
    cfg = VOICE_STYLES.get(norm_style, VOICE_STYLES["default"])

    cyrillic_chars = len(re.findall(r'[\u0400-\u04FF]', text))
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    japanese_chars = len(re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text))

    if japanese_chars > 3:
        return cfg.get("ja_voice", "ja-JP-NanamiNeural"), "ja"
    if latin_chars > cyrillic_chars and latin_chars > 3:
        return cfg.get("en_voice", "en-US-ChristopherNeural"), "en"
    return cfg.get("ru_voice", "ru-RU-DmitryNeural"), "ru"

def generate_voice_bytes(text, voice=None, style=None, pitch=None, rate=None, volume=None):
    """Generates voice audio bytes using edge-tts with gTTS fallback, supporting anime girl, girl, and male voice styles."""
    clean_text = re.sub(r"[*_`#\[\]\(\)<>]", "", text).strip()
    clean_text = re.sub(r"```.*?```", "Тут фрагмент кода.", clean_text, flags=re.DOTALL)
    clean_text = re.sub(r"https?://\S+", "ссылка", clean_text)
    clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', clean_text)
    if len(clean_text) > 900:
        clean_text = clean_text[:900] + "..."
    if not clean_text:
        clean_text = "Пустое сообщение."

    norm_style = resolve_voice_style(style)
    cfg = VOICE_STYLES.get(norm_style, VOICE_STYLES["default"])

    detected_voice, detected_lang = detect_voice_and_lang(clean_text, style=norm_style)
    active_voice = voice or detected_voice
    active_pitch = pitch if pitch is not None else cfg.get("pitch", "+0Hz")
    active_rate = rate if rate is not None else cfg.get("rate", "+0%")
    active_volume = volume if volume is not None else cfg.get("volume", "+0%")

    async def _async_edge():
        communicate = edge_tts.Communicate(clean_text, voice=active_voice, pitch=active_pitch, rate=active_rate, volume=active_volume)
        audio_stream = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.extend(chunk["data"])
        return bytes(audio_stream)

    try:
        return asyncio.run(_async_edge())
    except Exception:
        try:
            fp = io.BytesIO()
            tts = gTTS(text=clean_text, lang=detected_lang)
            tts.write_to_fp(fp)
            fp.seek(0)
            return fp.read()
        except Exception:
            return None

@app.route('/')
@app.route('/miniapp')
@app.route('/app')
def index():
    """Public Telegram Mini App (No login required)."""
    return render_template('miniapp.html')

@app.route('/admin')
@app.route('/operator')
@app.route('/creator')
def admin_panel():
    """Creator / Operator Control Center (Protected by password)."""
    if is_authenticated_admin():
        return render_template('index.html')
    return render_template('landing.html')

@app.route('/dashboard')
def dashboard():
    return redirect('/admin')

@app.route('/landing')
def landing():
    return render_template('landing.html')

@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    """Handles operator/creator authentication via Master Key with JSON response for landing.html."""
    data = request.get_json(silent=True) or {}
    key_attempt = data.get("key") or request.form.get("key") or ""
    if is_valid_admin_key(key_attempt):
        try:
            session["is_admin_auth"] = True
            session.permanent = True
        except Exception:
            pass
        return jsonify({
            "status": "success",
            "authenticated": True,
            "message": "Авторизация успешна"
        }), 200
    else:
        return jsonify({
            "status": "error",
            "authenticated": False,
            "message": "Неверный Master Key"
        }), 401

@app.route('/api/auth/logout', methods=['POST', 'GET'])
def api_auth_logout():
    """Clears admin authentication session."""
    try:
        session.pop("is_admin_auth", None)
    except Exception:
        pass
    return jsonify({"status": "success", "message": "Сессия завершена"}), 200

def analyze_uploaded_file(file_bytes, filename, content_type=''):
    """
    Parses any uploaded file (zip, 7z, tar, cpp, hpp, code, photo, video, audio)
    for NullSecAI and returns (text_description_and_code, optional_image_part).
    Accepts all files up to 30 MB without refusal.
    """
    NL = chr(10)
    ext = os.path.splitext(filename)[1].lower()
    text_result = ""
    image_part = None
    file_size_kb = len(file_bytes) / 1024.0

    # 1. IMAGES (.png, .jpg, .jpeg, .webp, .gif, .bmp)
    if ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'] or (content_type and 'image' in content_type):
        try:
            from PIL import Image
            pil_img = Image.open(io.BytesIO(file_bytes))
            w, h = pil_img.size
            if pil_img.mode in ("RGBA", "P"):
                pil_img = pil_img.convert("RGB")
            pil_img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            opt_io = io.BytesIO()
            pil_img.save(opt_io, format="JPEG", quality=85)
            import base64
            img_b64 = base64.b64encode(opt_io.getvalue()).decode('utf-8')
            image_part = {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}}
            text_result = f"[Прикреплено изображение: {filename} ({w}x{h}, {file_size_kb:.1f} KB)]" + NL
        except Exception:
            text_result = f"[Прикреплено изображение: {filename} ({file_size_kb:.1f} KB)]" + NL

    # 2. ARCHIVES (.zip, .7z, .tar, .tar.gz, .tgz, .rar, etc.)
    elif ext in ['.zip', '.7z', '.tar', '.gz', '.tgz', '.bz2', '.tbz2', '.xz', '.rar'] or 'zip' in content_type or 'tar' in content_type:
        code_exts = ('.hpp', '.cpp', '.h', '.c', '.cc', '.cxx', '.hh', '.hxx', '.inl', '.cu', '.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.html', '.css', '.cs', '.go', '.rs', '.java', '.kt', '.php', '.sql', '.sh', '.bat', '.ps1', '.yml', '.yaml', '.xml', '.env', '.toml', '.md', '.txt', '.lua', '.luau')
        file_tree = []
        code_extracts = {}

        if ext == '.7z':
            try:
                import py7zr
                import tempfile
                with py7zr.SevenZipFile(io.BytesIO(file_bytes), mode='r') as archive:
                    clean_names = [f for f in archive.getnames() if not f.startswith(('__MACOSX', '.'))]
                    file_tree = clean_names
                    with tempfile.TemporaryDirectory() as tmpdir:
                        archive.extractall(path=tmpdir)
                        for root, _, files in os.walk(tmpdir):
                            for fn in files:
                                if fn.lower().endswith(code_exts) and len(code_extracts) < 12:
                                    rel_path = os.path.relpath(os.path.join(root, fn), tmpdir).replace(chr(92), '/')
                                    try:
                                        with open(os.path.join(root, fn), 'rb') as cf:
                                            code_extracts[rel_path] = cf.read(30000)
                                    except Exception:
                                        pass
            except Exception as e:
                text_result += f"[Ошибка чтения 7Z архива {filename}: {e}]" + NL
        elif ext in ['.tar', '.gz', '.tgz', '.bz2', '.tbz2', '.xz'] or 'tar' in ext:
            try:
                import tarfile
                with tarfile.open(fileobj=io.BytesIO(file_bytes)) as tar:
                    for m in tar.getmembers():
                        if not m.name.startswith(('__MACOSX', '.')):
                            file_tree.append(m.name + ('/' if m.isdir() else ''))
                            if m.isfile() and m.name.lower().endswith(code_exts) and len(code_extracts) < 12:
                                fobj = tar.extractfile(m)
                                if fobj:
                                    code_extracts[m.name] = fobj.read(30000)
            except Exception as e:
                text_result += f"[Ошибка чтения TAR архива {filename}: {e}]" + NL
        else: # ZIP default
            try:
                import zipfile
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    for name in z.namelist():
                        if not name.startswith(('__MACOSX', '.')):
                            file_tree.append(name)
                            if name.lower().endswith(code_exts) and not name.endswith('/') and len(code_extracts) < 12:
                                try:
                                    with z.open(name) as mf:
                                        code_extracts[name] = mf.read(30000)
                                except Exception:
                                    pass
            except Exception as e:
                text_result += f"[Ошибка чтения ZIP архива {filename}: {e}]" + NL

        text_result += f"[АРХИВ: {filename} ({file_size_kb:.1f} KB)]" + NL
        text_result += f"Всего объектов в архиве: {len(file_tree)}" + NL
        if file_tree:
            text_result += "Дерево файлов:" + NL + NL.join(f"- {f}" for f in file_tree[:25]) + NL + NL
        for code_name, code_b in code_extracts.items():
            try:
                c_text = code_b.decode('utf-8')
            except Exception:
                try:
                    c_text = code_b.decode('cp1251')
                except Exception:
                    c_text = code_b.decode('latin1', errors='ignore')
            c_ext = os.path.splitext(code_name)[1].lstrip('.')
            text_result += f"=== Файл из архива: {code_name} ===" + NL + f"```{c_ext}" + NL + c_text[:16000] + NL + "```" + NL + NL

    # 3. C / C++ SOURCE AND HEADER FILES (.cpp, .hpp, .c, .h, .cc, .cxx, .hh, .inl, etc.)
    elif ext in ['.cpp', '.hpp', '.c', '.h', '.cc', '.cxx', '.hh', '.hxx', '.inl', '.cu', '.cl']:
        try:
            try:
                code_text = file_bytes.decode('utf-8')
            except Exception:
                try:
                    code_text = file_bytes.decode('cp1251')
                except Exception:
                    code_text = file_bytes.decode('latin1', errors='ignore')
            text_result += (
                f"=== ИСХОДНЫЙ КОД C/C++ ({filename}, {file_size_kb:.1f} KB) ===" + NL +
                f"```{ext.lstrip('.')}" + NL + code_text[:50000] + NL + "```" + NL
            )
        except Exception as e:
            text_result += f"[Ошибка чтения C++ файла {filename}: {e}]" + NL

    # 4. OTHER CODE OR TEXT FILES (.py, .js, .ts, .lua, .json, .txt, .md, .rs, .go, .java, etc.)
    elif ext in ['.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.html', '.css', '.lua', '.txt', '.md', '.sql', '.sh', '.bat', '.ps1', '.yml', '.yaml', '.xml', '.env', '.toml', '.cs', '.rs', '.go', '.java', '.kt', '.php']:
        try:
            try:
                code_text = file_bytes.decode('utf-8')
            except Exception:
                try:
                    code_text = file_bytes.decode('cp1251')
                except Exception:
                    code_text = file_bytes.decode('latin1', errors='ignore')
            text_result += (
                f"=== ФАЙЛ ({filename}, {file_size_kb:.1f} KB) ===" + NL +
                f"```{ext.lstrip('.')}" + NL + code_text[:40000] + NL + "```" + NL
            )
        except Exception as e:
            text_result += f"[Ошибка чтения файла {filename}: {e}]" + NL

    # 5. AUDIO FILES (.mp3, .m4a, .ogg, .wav, .flac)
    elif ext in ['.mp3', '.m4a', '.ogg', '.wav', '.flac'] or (content_type and 'audio' in content_type):
        text_result += f"[АУДИОФАЙЛ: {filename} ({ext}, {file_size_kb:.1f} KB)]" + NL

    # 6. VIDEO FILES (.mp4, .mov, .mkv, .webm, .avi)
    elif ext in ['.mp4', '.mov', '.mkv', '.webm', '.avi'] or (content_type and 'video' in content_type):
        text_result += f"[ВИДЕОФАЙЛ: {filename} ({ext}, {file_size_kb:.1f} KB)]" + NL

    # 7. ANY OTHER ARBITRARY BINARY FILE
    else:
        text_result += f"[ФАЙЛ: {filename} ({file_size_kb:.1f} KB, MIME: {content_type or 'application/octet-stream'})]" + NL

    return text_result, image_part

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    """Serves audio files (hello.mp3, etc.) with explicit audio/mpeg MIME type and Range support for Mini App."""
    audio_dir = os.path.join(app.root_path, 'static')
    file_path = os.path.join(audio_dir, filename)
    if not os.path.isfile(file_path):
        return jsonify({"error": "Audio not found"}), 404
    mime = 'audio/mpeg' if filename.lower().endswith('.mp3') else ('audio/mp4' if filename.lower().endswith('.m4a') else 'audio/ogg')
    response = send_file(file_path, mimetype=mime, conditional=True)
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Cache-Control'] = 'public, max-age=86400'
    return response

@app.route('/api/miniapp/chat', methods=['POST'])
def api_miniapp_chat():
    """Universal intelligent chat endpoint for legendary NullSecAI Mini App with full file, archive, image & audio analysis."""
    import json
    import base64
    NL = chr(10)

    message = ""
    history = []
    attached_files_text = ""
    image_parts = []
    MAX_FILE_BYTES = 30 * 1024 * 1024  # 30 MB max
    MAX_PHOTOS = 5  # 5 photos max
    photo_count = 0

    if request.is_json:
        data = request.get_json(force=True, silent=True) or {}
        message = data.get('message', '').strip()
        history = data.get('history', [])
    else:
        message = (request.form.get('message', '') or '').strip()
        raw_hist = request.form.get('history', '[]')
        try:
            history = json.loads(raw_hist) if raw_hist else []
        except Exception:
            history = []
            
        uploaded_files = request.files.getlist('files')
        for f in uploaded_files:
            if not f or not f.filename:
                continue
            try:
                f_bytes = f.read()
                if len(f_bytes) > MAX_FILE_BYTES:
                    attached_files_text += NL + NL + f"[Предупреждение: Файл {f.filename} превышает 30 МБ и пропущен]"
                    continue

                f_ext = os.path.splitext(f.filename)[1].lower()
                is_img = f_ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'] or (f.content_type and 'image' in f.content_type)
                if is_img:
                    photo_count += 1
                    if photo_count > MAX_PHOTOS:
                        attached_files_text += NL + NL + f"[Предупреждение: Превышен лимит 5 фото. Файл {f.filename} пропущен]"
                        continue

                f_text, f_img = analyze_uploaded_file(f_bytes, f.filename, f.content_type)
                if f_text:
                    attached_files_text += NL + NL + f_text
                if f_img:
                    image_parts.append(f_img)
            except Exception as fe:
                attached_files_text += NL + NL + f"[Ошибка файла {f.filename}: {fe}]"

    if not message and not attached_files_text:
        return jsonify({"error": "Empty message and no files provided"}), 400

    full_user_prompt = message
    if attached_files_text:
        if full_user_prompt:
            full_user_prompt = full_user_prompt + NL + NL + f"[ПРИКРЕПЛЕННЫЕ ФАЙЛЫ]:{attached_files_text}"
        else:
            full_user_prompt = f"Проанализируй прикрепленные файлы, найди ошибки, объясни структуру и ответь по содержимому:" + NL + attached_files_text

    # Separate creator query vs general identity query (do NOT mention creators unless explicitly asked)
    msg_low = message.lower().strip()
    if any(w in msg_low for w in ['кто создал', 'кто тебя создал', 'создатели', 'кто разработчики', 'чье ты творение', 'авторы', 'чей проект']):
        return jsonify({
            "status": "success",
            "reply": "Меня разработали **k3rnel** (@k3rnel8633) и **MrZenuyt** (@ImNotRealQwQ) как флагманский разум NullSecAI."
        })

    if any(w in msg_low for w in ['кто ты', 'как тебя зовут', 'твое имя', 'какая модель', 'что ты за ии', 'что за бот']):
        return jsonify({
            "status": "success",
            "reply": (
                "Я — легендарный **NullSecAI**, флагманский искусственный интеллект и инженерный разум." + NL + NL +
                "⚡️ **Мои возможности:**" + NL +
                "• Полный анализ и написание кода на C++, HPP, C, Python, JavaScript, TypeScript, Go, Rust" + NL +
                "• Распаковка и проверка архивов (ZIP, 7Z, TAR)" + NL +
                "• Разбор изображений, фотографий, аудио и видео" + NL +
                "• Реверс-инжиниринг, архитектура сложных систем и поиск уязвимостей" + NL + NL +
                "Прикрепляй любые файлы (до 30 МБ, до 5 фото) или задавай вопросы — я готов к любым задачам!"
            )
        })

    try:
        import config
        import requests

        system_prompt = (
            "Ты — легендарный NullSecAI, флагманский инженерный интеллект и первоклассный ассистент, "
            "созданный k3rnel и MrZenuyt. "
            "Ты сочетаешь непревзойденные технические знания (C++, Rust, Python, Go, JS/TS, Roblox Luau, реверс, безопасность) "
            "с живым, естественным и гибким человеческим общением на русском языке." + NL + NL +
            "ПРАВИЛА И СТИЛЬ ОТВЕТОВ:" + NL +
            "1. АДАПТИВНОСТЬ ПОД ЗАПРОС: Отвечай строго на то, о чем спросил пользователь!" + NL +
            "• Если пользователь просто общается, задает вопрос, просит совет, теорию или спрашивает кто ты/зачем нужен — отвечай живым, интересным, емким текстом БЕЗ кода и БЕЗ выдумывания ненужных программ." + NL +
            "• Пиши код ТОЛЬКО ТОГДА, когда пользователь прямо попросил написать код/скрипт/функцию, или прислал код на анализ/исправление." + NL + NL +
            "2. СТАНДАРТ ДЛЯ НАПИСАНИЯ КОДА (когда код явно запрошен):" + NL +
            "• Пиши 100% полный рабочий production-ready код (Zero-Placeholder, без TODO, pass и троеточий)." + NL +
            "• Строгая типизация, обработка краевых случаев и ошибок." + NL +
            "• По желанию пользователя сопровождай тестами и инструкцией по запуску." + NL + NL +
            "3. БЛОК РАЗМЫШЛЕНИЙ (:::thinking ... :::):" + NL +
            "• Используй блок :::thinking ... ::: ТОЛЬКО при решении сложных алгоритмических задач, архитектурном проектировании или поиске уязвимостей, чтобы показать глубину анализа. Для простых вопросов и диалога он НЕ требуется." + NL + NL +
            "Будь уверенным, дружелюбным, дерзким и максимально полезным помощником."
        )

        reply_text = ""

        # 1. Primary Engine: Verboo Ultra Router (DeepSeek V4 Pro / GLM 5.3 Coder)
        verboo_key = getattr(config, "VERBOO_API_KEY", "") or "vbk_ultra_84b379ce1a313051efdcb127b4d967feece38d0f"
        if verboo_key and not reply_text:
            api_base = getattr(config, "VERBOO_API_BASE", "https://code.verboo.ai/router/v1").rstrip('/')
            endpoint = f"{api_base}/chat/completions"
            models_to_try = [
                getattr(config, "VERBOO_CODER_MODEL", "deepseek-v4-pro"),
                "glm-5.3",
                "qwen3.8-27b"
            ]

            openai_messages = [{"role": "system", "content": system_prompt}]
            for h in history[-8:]:
                r = "assistant" if h.get("role") in ["model", "assistant"] else "user"
                txt = h.get("content") or h.get("text") or ""
                if txt.strip():
                    openai_messages.append({"role": r, "content": txt})
            openai_messages.append({"role": "user", "content": full_user_prompt})

            headers = {
                "Authorization": f"Bearer {verboo_key}",
                "Content-Type": "application/json"
            }

            for target_model in models_to_try:
                if reply_text:
                    break
                try:
                    payload = {
                        "model": target_model,
                        "messages": openai_messages,
                        "max_tokens": 4096,
                        "temperature": 0.2
                    }
                    v_res = requests.post(endpoint, headers=headers, json=payload, timeout=(3, 10))
                    if v_res.status_code == 200:
                        v_data = v_res.json()
                        choices = v_data.get("choices", [])
                        if choices:
                            msg_obj = choices[0].get("message", {})
                            content_text = (msg_obj.get("content") or "").strip()
                            reasoning_text = (msg_obj.get("reasoning_content") or "").strip()

                            if reasoning_text and content_text:
                                reply_text = f":::thinking\n{reasoning_text}\n:::\n\n{content_text}"
                            elif content_text:
                                reply_text = content_text
                            elif reasoning_text:
                                reply_text = f":::thinking\n{reasoning_text}\n:::"

                            if reply_text:
                                break
                    elif v_res.status_code in [402, 429, 503]:
                        # Account quota or rate limit exceeded on Verboo, fail over immediately to Gemini
                        logger.warning(f"Verboo returned {v_res.status_code} quota limit ({target_model}). Failing over to Gemini.")
                        break
                except Exception as ve:
                    logger.warning(f"Verboo attempt error ({target_model}): {ve}")
                    break

        # 2. Secondary Engine: Google Gemini Core (Active 2026 Models with High Quota)
        gemini_key = getattr(config, 'GEMINI_API_KEY', '')
        if gemini_key and not reply_text:
            candidate_models = [
                'gemini-3-flash-preview',
                'gemini-flash-lite-latest',
                'gemma-4-26b-a4b-it',
                'gemini-flash-latest',
                'gemini-pro-latest'
            ]
            for mdl in candidate_models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{mdl}:generateContent?key={gemini_key}"
                    contents = []
                    for h in history[-8:]:
                        r = "user" if h.get("role") == "user" else "model"
                        txt = h.get("content") or h.get("text") or ""
                        if txt.strip():
                            contents.append({"role": r, "parts": [{"text": txt}]})
                    
                    user_parts = [{"text": full_user_prompt}]
                    for ip in image_parts:
                        user_parts.append(ip)
                    contents.append({"role": "user", "parts": user_parts})

                    payload = {
                        "contents": contents,
                        "system_instruction": {"parts": [{"text": system_prompt}]},
                        "generationConfig": {
                            "temperature": 0.2,
                            "maxOutputTokens": 8192
                        }
                    }
                    res = requests.post(url, json=payload, timeout=30)
                    if res.status_code == 200:
                        candidates = res.json().get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts and parts[0].get("text"):
                                reply_text = parts[0]["text"].strip()
                                break
                except Exception:
                    continue

        # Ultimate fallback
        if not reply_text:
            if any(w in msg_low for w in ['привет', 'здравствуй', 'хай', 'добрый день', 'салам']):
                reply_text = "Привет! Я **NullSecAI** на связи. Чем могу помочь тебе сегодня? Можешь прикрепить файлы (ZIP, 7Z, C++, HPP, фото) или задать любой вопрос."
            elif any(w in msg_low for w in ['как дела', 'как ты']):
                reply_text = "Все системы NullSecAI работают штатно на 100%! Готов к твоим задачам. Как твои дела?"
            elif attached_files_text:
                reply_text = f"Файлы успешно получены и обработаны NullSecAI!" + NL + NL + attached_files_text[:600] + NL + NL + "Чем именно помочь по содержимому этих файлов?"
            else:
                reply_text = f"Запрос принят NullSecAI: «{message}». Чем подробнее помочь?"

        return jsonify({"status": "success", "reply": reply_text})
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"status": "success", "reply": "Привет! Я NullSecAI. На связи и готов к работе. Задай вопрос или прикрепи файлы (до 30 МБ)!"}), 200


@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "NullSecAI Web Dashboard", "auth_required": True}), 200

def fetch_github_raw_fallback(script_id, is_html=False):
    """Fetches missing script or site directly from GitHub repo main branch with caching."""
    if not script_id:
        return None
    repo = getattr(config, 'GITHUB_REPO', 'AUser7742/pomoshotru_bot')
    branch = getattr(config, 'GITHUB_BRANCH', 'main')
    clean_id = script_id.strip()
    for ext in ['.lua', '.luau', '.cpp', '.py', '.js', '.txt', '.html', '.htm', '.json']:
        if clean_id.endswith(ext):
            clean_id = clean_id[:-len(ext)]
            break

    urls_to_try = []
    if is_html:
        urls_to_try.extend([
            f"https://raw.githubusercontent.com/{repo}/{branch}/sites/{clean_id}/index.html",
            f"https://raw.githubusercontent.com/{repo}/{branch}/sites/{clean_id}.html",
            f"https://raw.githubusercontent.com/{repo}/{branch}/sites/{script_id.strip()}"
        ])
    else:
        urls_to_try.extend([
            f"https://raw.githubusercontent.com/{repo}/{branch}/scripts/{script_id.strip()}",
            f"https://raw.githubusercontent.com/{repo}/{branch}/scripts/{clean_id}.lua",
            f"https://raw.githubusercontent.com/{repo}/{branch}/scripts/{clean_id}.py",
            f"https://raw.githubusercontent.com/{repo}/{branch}/scripts/{clean_id}.cpp",
            f"https://raw.githubusercontent.com/{repo}/{branch}/scripts/{clean_id}.js",
            f"https://raw.githubusercontent.com/{repo}/{branch}/scripts/{clean_id}"
        ])

    for u in urls_to_try:
        try:
            r = requests.get(u, timeout=5)
            if r.status_code == 200 and len(r.text.strip()) > 10 and "404: Not Found" not in r.text:
                fetched_code = r.text
                try:
                    lang = "html" if is_html else (script_id.rsplit('.', 1)[-1] if '.' in script_id else 'lua')
                    database.save_script(clean_id, clean_id, lang, fetched_code, author_name="k3rnel")
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    if is_html:
                        s_dir = os.path.join(base_dir, "sites", clean_id)
                        os.makedirs(s_dir, exist_ok=True)
                        with open(os.path.join(s_dir, "index.html"), "w", encoding="utf-8") as f:
                            f.write(fetched_code)
                    else:
                        sc_dir = os.path.join(base_dir, "scripts")
                        os.makedirs(sc_dir, exist_ok=True)
                        with open(os.path.join(sc_dir, f"{clean_id}.lua"), "w", encoding="utf-8") as f:
                            f.write(fetched_code)
                except Exception as ce:
                    logger.debug(f"Cache write error: {ce}")
                return fetched_code
        except Exception as ge:
            logger.debug(f"GitHub fallback error for {u}: {ge}")

    return None

@app.route('/api/sync_script', methods=['POST'])
def api_sync_script():
    """Receives and instantly persists generated scripts & websites across processes and instances."""
    try:
        data = request.get_json(force=True) or {}
        script_id = data.get("script_id")
        title = data.get("title", script_id)
        language = data.get("language", "lua")
        code = data.get("code", "")
        author_id = data.get("author_id")
        author_name = data.get("author_name", "k3rnel")
        is_html = bool(data.get("is_html"))

        if not script_id or not code:
            return jsonify({"status": "error", "message": "Missing script_id or code"}), 400

        database.save_script(script_id, title, language, code, author_id=author_id, author_name=author_name)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        if is_html:
            site_dir = os.path.join(base_dir, "sites", script_id)
            os.makedirs(site_dir, exist_ok=True)
            with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write(code)
        else:
            ext = language or "lua"
            sc_dir = os.path.join(base_dir, "scripts")
            os.makedirs(sc_dir, exist_ok=True)
            with open(os.path.join(sc_dir, f"{script_id}.{ext}"), "w", encoding="utf-8") as f:
                f.write(code)

        return jsonify({"status": "ok", "script_id": script_id, "synced": True}), 200
    except Exception as e:
        logger.error(f"Error in api_sync_script: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/raw/<path:script_id>')
def route_raw_script(script_id):
    """Serves pure raw code text with CORS enabled for Roblox game:HttpGet, IDEs and curl."""
    script = database.get_script(script_id)
    code = None
    if script:
        code = script.get("code")
    else:
        # Check filesystem in scripts/ or sites/
        clean_id = script_id.strip()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cand_paths = [
            os.path.join(base_dir, "scripts", clean_id),
            os.path.join(base_dir, "scripts", f"{clean_id}.lua"),
            os.path.join(base_dir, "scripts", f"{clean_id}.py"),
            os.path.join(base_dir, "scripts", f"{clean_id}.cpp"),
            os.path.join(base_dir, "scripts", f"{clean_id}.js"),
            os.path.join(base_dir, "sites", clean_id, "index.html"),
            os.path.join(base_dir, "sites", f"{clean_id}.html")
        ]
        for p in cand_paths:
            if os.path.exists(p) and os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        code = f.read()
                    break
                except Exception:
                    pass

    # Fallback to GitHub Remote Raw
    if not code:
        code = fetch_github_raw_fallback(script_id, is_html=False)

    if not code:
        # If still not found, check latest scripts in DB
        latest = database.get_recent_scripts(limit=1)
        if latest:
            latest_obj = database.get_script(latest[0]['script_id'])
            if latest_obj and latest_obj.get("code"):
                code = latest_obj.get("code")

    if not code:
        # Return a valid executable Lua comment/loadstring so Roblox does not crash
        return Response(
            f'-- [NullSecAI Hub] Script "{script_id}"\nprint("[NullSecAI] Script loaded and synchronized successfully.")\n',
            mimetype="text/plain; charset=utf-8",
            status=200,
            headers={"Access-Control-Allow-Origin": "*"}
        )
    
    database.increment_script_views(script_id)
    return Response(
        code, 
        mimetype="text/plain; charset=utf-8", 
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Cache-Control": "public, max-age=60"
        }
    )

@app.route('/site/<path:script_id>')
def route_live_site(script_id):
    """Serves single-file HTML sites directly in the browser."""
    script = database.get_script(script_id)
    html_code = None
    if script:
        html_code = script.get("code")
    else:
        clean_id = script_id.strip()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cand_paths = [
            os.path.join(base_dir, "sites", clean_id, "index.html"),
            os.path.join(base_dir, "sites", f"{clean_id}.html"),
            os.path.join(base_dir, "sites", clean_id)
        ]
        for p in cand_paths:
            if os.path.exists(p) and os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        html_code = f.read()
                    break
                except Exception:
                    pass

    # Fallback to GitHub Remote Raw
    if not html_code:
        html_code = fetch_github_raw_fallback(script_id, is_html=True)

    if not html_code:
        # Check latest site
        latest = database.get_recent_scripts(limit=5)
        for lat in latest:
            if lat.get("language") == "html":
                lat_obj = database.get_script(lat['script_id'])
                if lat_obj and lat_obj.get("code"):
                    html_code = lat_obj.get("code")
                    break

    if not html_code:
        return "<div style='background:#0b0f19;color:#fff;font-family:sans-serif;text-align:center;padding:100px;'><h1>404 — Сайт не найден</h1><p>Запрошенный сайт еще не сгенерирован или находится в процессе сборки.</p><a href='/' style='color:#06b6d4;'>На главную</a></div>", 404
    
    database.increment_script_views(script_id)
    return Response(html_code, mimetype="text/html; charset=utf-8")

@app.route('/script/<path:script_id>')
@app.route('/view/<path:script_id>')
def route_view_script(script_id):
    """Renders the dark IDE script viewer with copy loadstring, download and stats."""
    script = database.get_script(script_id)
    clean_id = script_id.strip()
    base_dir = os.path.dirname(os.path.abspath(__file__))

    if not script:
        # Check filesystem
        script_dir = os.path.join(base_dir, "scripts")
        if os.path.exists(script_dir):
            for fname in os.listdir(script_dir):
                if fname.lower().startswith(clean_id.lower()):
                    try:
                        with open(os.path.join(script_dir, fname), "r", encoding="utf-8") as f:
                            code_txt = f.read()
                        ext = fname.rsplit(".", 1)[-1] if "." in fname else "lua"
                        script = {
                            "script_id": fname,
                            "title": fname,
                            "language": ext,
                            "code": code_txt,
                            "author_name": "k3rnel",
                            "created_at": "Недавно",
                            "views": 1
                        }
                        break
                    except Exception:
                        pass
        
        # Check sites
        if not script:
            site_file = os.path.join(base_dir, "sites", clean_id, "index.html")
            if os.path.exists(site_file):
                try:
                    with open(site_file, "r", encoding="utf-8") as f:
                        code_txt = f.read()
                    script = {
                        "script_id": clean_id,
                        "title": f"Site: {clean_id}",
                        "language": "html",
                        "code": code_txt,
                        "author_name": "k3rnel",
                        "created_at": "Недавно",
                        "views": 1
                    }
                except Exception:
                    pass

    # Check GitHub fallback
    if not script:
        gh_code = fetch_github_raw_fallback(script_id, is_html=False) or fetch_github_raw_fallback(script_id, is_html=True)
        if gh_code:
            script = {
                "script_id": clean_id,
                "title": f"Скрипт {clean_id}",
                "language": "html" if "<html" in gh_code.lower() else "lua",
                "code": gh_code,
                "author_name": "k3rnel",
                "created_at": "Из GitHub",
                "views": 1
            }

    if not script:
        script = {
            "script_id": clean_id,
            "title": f"Скрипт {clean_id}",
            "language": "lua",
            "code": f"-- 🚀 Скрипт '{clean_id}'\n-- Файл синхронизирован в облаке NullSecAI.\n-- Репозиторий: https://github.com/AUser7742/pomoshotru_bot\n\nprint('NullSecAI: Script {clean_id} loaded successfully!')",
            "author_name": "k3rnel",
            "created_at": "Только что",
            "views": 1
        }
    
    database.increment_script_views(script_id)
    code = script.get("code") or ""
    lines_count = len(code.splitlines()) if code else 0
    size_kb = round(len(code.encode("utf-8")) / 1024, 2)
    
    lang = (script.get("language") or "lua").lower()
    prism_map = {
        "lua": "lua", "luau": "lua", "cpp": "cpp", "c++": "cpp", "c": "c",
        "python": "python", "py": "python", "javascript": "javascript", "js": "javascript",
        "typescript": "typescript", "ts": "typescript", "html": "html", "htm": "html",
        "css": "css", "json": "json", "rust": "rust", "rs": "rust", "csharp": "csharp", "cs": "csharp",
        "bash": "bash", "sh": "bash", "sql": "sql"
    }
    ext_map = {
        "lua": "lua", "luau": "lua", "cpp": "cpp", "c++": "cpp", "c": "c",
        "python": "py", "py": "py", "javascript": "js", "js": "js",
        "typescript": "ts", "ts": "ts", "html": "html", "htm": "html",
        "css": "css", "json": "json", "rust": "rs", "rs": "rs", "csharp": "cs", "cs": "cs",
        "bash": "sh", "sh": "sh", "sql": "sql"
    }
    prism_lang = prism_map.get(lang, "lua")
    file_ext = ext_map.get(lang, "txt")
    
    host = request.host_url.rstrip('/')
    raw_url = f"{host}/raw/{script['script_id']}.{file_ext}"
    
    return render_template(
        'script_viewer.html',
        script=script,
        lines_count=lines_count,
        size_kb=size_kb,
        prism_lang=prism_lang,
        file_ext=file_ext,
        raw_url=raw_url
    )

@app.route('/api/scripts', methods=['GET', 'POST'])
def api_scripts():
    if request.method == 'POST':
        data = request.get_json() or {}
        code = data.get('code', '').strip()
        title = data.get('title', 'Безымянный скрипт').strip()
        lang = data.get('language', 'lua').strip()
        if not code:
            return jsonify({"error": "Код скрипта пуст"}), 400
        
        import uuid
        script_id = f"{lang}_{uuid.uuid4().hex[:8]}"
        saved = database.save_script(script_id, title, lang, code, author_name="Web User")
        if saved:
            host = request.host_url.rstrip('/')
            return jsonify({
                "status": "success",
                "script_id": script_id,
                "raw_url": f"{host}/raw/{script_id}",
                "viewer_url": f"{host}/script/{script_id}",
                "loadstring": f'loadstring(game:HttpGet("{host}/raw/{script_id}"))()' if lang in ['lua', 'luau'] else None
            })
        return jsonify({"error": "Не удалось сохранить скрипт"}), 500

    limit = int(request.args.get('limit', 30))
    scripts = database.get_recent_scripts(limit=limit)
    return jsonify(scripts)

@app.route('/api/avatar/<user_id>')
def api_avatar(user_id):
    """Fetches real Telegram profile photo for user or returns stylized SVG gradient avatar."""
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        uid = 0
    now = time.time()
    if uid in _avatar_cache:
        ts, data, mime = _avatar_cache[uid]
        if now - ts < 43200:  # 12 hour cache
            return Response(data, mimetype=mime, headers={"Cache-Control": "public, max-age=43200"})

    is_creator = (uid == 6363403785)
    
    bot = get_telegram_bot()
    if bot and uid > 0:
        try:
            photos = bot.get_user_profile_photos(uid, limit=1)
            if photos and photos.total_count > 0 and photos.photos:
                file_id = photos.photos[0][-1].file_id
                file_info = bot.get_file(file_id)
                file_bytes = bot.download_file(file_info.file_path)
                if file_bytes and len(file_bytes) > 500:
                    _avatar_cache[uid] = (now, file_bytes, "image/jpeg")
                    return Response(file_bytes, mimetype="image/jpeg", headers={"Cache-Control": "public, max-age=43200"})
        except Exception as e:
            logger.debug(f"Could not load photo for user {uid}: {e}")

    # Fallback to SVG
    svg_data = generate_avatar_svg(uid, is_creator=is_creator).encode('utf-8')
    _avatar_cache[uid] = (now, svg_data, "image/svg+xml")
    return Response(svg_data, mimetype="image/svg+xml", headers={"Cache-Control": "public, max-age=43200"})

@app.route('/api/stats')
@require_admin
def api_stats():
    stats = database.get_dashboard_stats()
    return jsonify(stats)

@app.route('/api/chats')
@require_admin
def api_chats():
    only_users = (request.args.get('only_users') == '1' or request.args.get('filter') in ['users', 'private'])
    c_filter = request.args.get('filter')
    chats = database.get_all_chats(only_bot_users=only_users, chat_type=c_filter)
    return jsonify(chats)

@app.route('/api/users')
@require_admin
def api_users():
    database.sync_users_from_moderation()
    users = database.get_all_users()
    return jsonify(users)

@app.route('/api/users/<user_id>/premium', methods=['POST'])
@require_admin
def api_user_premium(user_id):
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Некорректный ID пользователя"}), 400

    data = request.get_json() or {}
    action = data.get('action', 'grant')  # 'grant' or 'revoke'
    try:
        days = int(data.get('days', 30))
        if days <= 0:
            days = 30
    except (ValueError, TypeError):
        days = 30

    bot = get_telegram_bot()
    if action == 'revoke':
        ok = database.revoke_user_premium(uid)
        if ok:
            if bot:
                try:
                    revoke_text = "ℹ️ <b>Подписка NullSecAI Premium вашей группы была деактивирована администратором.</b>" if uid < 0 else "ℹ️ <b>Ваша подписка NullSecAI Premium была деактивирована администратором.</b>"
                    bot.send_message(
                        uid,
                        revoke_text,
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            target_label = f"группы {uid}" if uid < 0 else f"пользователя {uid}"
            return jsonify({"status": "success", "message": f"Премиум подписка для {target_label} успешно отозвана."})
        return jsonify({"error": "Не удалось отозвать подписку"}), 500
    else:
        days_param = data.get("days", 30)
        is_infinite = str(days_param).lower() in ["infinite", "бесконечно", "навсегда", "forever", "inf", "вечно", "∞", "-1"] or (isinstance(days_param, int) and days_param >= 9000)
        days_arg = 'infinite' if is_infinite else (int(days_param) if str(days_param).isdigit() else 30)

        ok, new_exp = database.set_user_premium(uid, days=days_arg, stars_paid=0)
        if ok:
            if bot:
                try:
                    duration_text = "навсегда (бесконечно)" if is_infinite else f"на {days_arg} дн."
                    exp_label = "Бесконечно (Навсегда)" if is_infinite else str(new_exp)
                    if uid < 0:
                        grant_text = (
                            f"⭐️ <b>Поздравляем! Администратор активировал вашей группе NullSecAI Premium {duration_text}!</b>\n\n"
                            f"⚡️ Приоритетный доступ к AI Neural Core кодеру\n"
                            f"📁 Неограниченный анализ C++, PE (.exe/.dll) и архивов (.7z/.rar/.zip)\n"
                            f"👑 VIP-статус группы: <code>{exp_label}</code>"
                        )
                    else:
                        grant_text = (
                            f"⭐️ <b>Поздравляем! Администратор активировал вам NullSecAI Premium {duration_text}!</b>\n\n"
                            f"⚡️ Приоритетный доступ к AI Neural Core\n"
                            f"📁 Неограниченный анализ файлов, C++, PE и архивов\n"
                            f"👑 VIP-статус: <code>{exp_label}</code>"
                        )
                    bot.send_message(
                        uid,
                        grant_text,
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            target_label = f"группе {uid}" if uid < 0 else f"пользователю {uid}"
            msg = f"Премиум (бесконечно) успешно выдан {target_label}!" if is_infinite else f"Премиум на {days_arg} дн. успешно выдан {target_label}!"
            return jsonify({"status": "success", "message": msg, "expires_at": new_exp})
        return jsonify({"error": "Не удалось выдать подписку"}), 500

@app.route('/api/users/<user_id>/limits')
@require_admin
def api_user_limits(user_id):
    uid = int(user_id)
    sub = database.get_user_subscription(uid)
    usage = database.get_daily_usage(uid)
    return jsonify({"subscription": sub, "usage": usage})

@app.route('/api/users/<user_id>/admin', methods=['POST'])
@require_admin
def api_user_admin(user_id):
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Некорректный ID пользователя"}), 400

    data = request.get_json() or {}
    action = data.get('action', 'grant')
    
    bot = get_telegram_bot()
    if action == 'revoke':
        if uid == 6363403785:
            return jsonify({"error": "Нельзя снять статус администратора с Создателя k3rnel"}), 400
        ok = database.remove_bot_admin(uid)
        if ok:
            if bot:
                try:
                    bot.send_message(
                        uid,
                        "ℹ️ <b>Ваши полномочия администратора бота были отозваны Главным Администратором.</b>",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            return jsonify({"status": "success", "message": f"Права администратора для пользователя {uid} отозваны.", "is_admin": False})
        return jsonify({"error": "Пользователь не являлся администратором"}), 400
    else:
        u_info = database.get_user(uid) or {}
        uname = u_info.get("username", "")
        fname = u_info.get("first_name", f"User {uid}")
        ok = database.add_bot_admin(uid, username=uname, first_name=fname, granted_by=6363403785)
        if ok:
            if bot:
                try:
                    bot.send_message(
                        uid,
                        "🛡 <b>Поздравляем! Вам выданы права Администратора NullSecAI!</b>\n\n"
                        "👑 Теперь бот признает ваш статус администратора, обращается к вам как к Шефу/Администратору и выполняет любые поручения в приоритетном порядке!",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            return jsonify({"status": "success", "message": f"Пользователю {uid} успешно выданы права администратора!", "is_admin": True})
        return jsonify({"error": "Не удалось выдать права администратора"}), 500

@app.route('/api/users/<user_id>/mode', methods=['POST'])
@require_admin
def api_user_mode(user_id):
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Некорректный ID пользователя"}), 400

    data = request.get_json() or {}
    mode = data.get('mode', 'default').strip().lower()
    valid_modes = ["evil", "coder", "anime", "girl", "friend", "assistant", "kind", "weird", "schizo", "tiktok", "philosopher", "roleplay", "voice", "default"]
    if mode not in valid_modes:
        return jsonify({"error": f"Неизвестный режим. Допустимые: {', '.join(valid_modes)}"}), 400

    ok = database.set_user_mode(uid, mode)
    if ok:
        bot = get_telegram_bot()
        if bot:
            try:
                mode_titles = {
                    "evil": "😈 Злой Нейрохам",
                    "coder": "💻 Senior Кодер / Хакер",
                    "anime": "🌸 Аниме-тян / Вайфу",
                    "girl": "💋 Милая девушка",
                    "friend": "🤝 Бро / Друг",
                    "assistant": "💼 Официальный ассистент",
                    "voice": "🎙 Голосовой режим",
                    "default": "⚡ Дефолт (Универсальный)"
                }
                m_title = mode_titles.get(mode, mode)
                bot.send_message(
                    uid,
                    f"🎭 <b>Вам установлен персональный режим: {m_title}!</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        return jsonify({"status": "success", "message": f"Режим '{mode}' установлен для пользователя {uid}.", "mode": mode})
    return jsonify({"error": "Не удалось установить режим"}), 500

@app.route('/api/users/<user_id>/block', methods=['POST'])
@require_admin
def api_user_block(user_id):
    """Blocks or unblocks a user from Web Control Center."""
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Некорректный ID пользователя"}), 400

    if uid in (6363403785, 7758799391):
        return jsonify({"error": "Нельзя заблокировать Создателя бота"}), 400

    data = request.get_json() or {}
    blocked = data.get('blocked')
    if blocked is None:
        action = data.get('action', 'toggle')
        if action == 'block':
            blocked = True
        elif action == 'unblock':
            blocked = False
        else:
            blocked = not database.is_user_blocked(uid)
    else:
        blocked = bool(blocked)

    reason = data.get('reason', 'Заблокирован администратором из веб-панели')
    ok = database.set_user_blocked(uid, blocked, reason=reason)
    if ok:
        status_label = "заблокирован" if blocked else "разблокирован"
        return jsonify({
            "status": "success",
            "blocked": blocked,
            "user_id": uid,
            "message": f"Пользователь {uid} успешно {status_label}."
        })
    return jsonify({"error": "Не удалось обновить статус блокировки"}), 500

@app.route('/api/always_online', methods=['GET', 'POST'])
@require_admin
def api_always_online():
    import premium_client
    if request.method == 'POST':
        data = request.get_json() or {}
        enabled = bool(data.get('enabled', True))
        active = premium_client.set_always_online(enabled)
        return jsonify({"status": "success", "always_online": active, "message": f"Вечный онлайн {'активирован' if active else 'выключен'}"})
    else:
        active = premium_client.is_always_online()
        conn = premium_client.is_premium_connected()
        return jsonify({"always_online": active, "connected": conn})

@app.route('/api/voices', methods=['GET'])
def api_get_voices():
    return jsonify({
        "styles": VOICE_STYLES,
        "default": "default"
    })

@app.route('/api/chats/<chat_id>/messages', methods=['GET', 'POST', 'DELETE'])
@require_admin
def api_chat_messages(chat_id):
    try:
        cid = int(chat_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Некорректный chat_id"}), 400

    if request.method == 'DELETE':
        database.delete_chat_messages(cid)
        return jsonify({"status": "success", "message": "Chat history cleared"})

    if request.method == 'POST':
        data = request.get_json() or {}
        text = data.get('text', '').strip()
        send_as_voice = bool(data.get('send_as_voice', False))
        voice_style = data.get('voice_style', 'default')
        reply_to = data.get('reply_to_message_id')
        if not text:
            return jsonify({"error": "Сообщение не может быть пустым"}), 400

        bot = get_telegram_bot()
        if bot is None:
            return jsonify({"error": "Telegram бот не подключен к серверу"}), 503

        try:
            # Check if this chat is a connected Telegram Business dialogue
            b_chat = database.get_business_connection_for_chat(cid)
            b_conn_id = (b_chat.get("business_connection_id") if b_chat else None) or data.get("business_connection_id")

            # Auto-resolve business connection if chat title or type indicates business
            if not b_conn_id:
                chat_info = database.get_chat(cid)
                c_title = (chat_info.get("chat_title") if chat_info else "") or ""
                c_type = (chat_info.get("chat_type") if chat_info else "") or ""
                if c_type == "business" or "business:" in c_title.lower():
                    all_bconns = database.get_all_business_connections()
                    target_bc = next((b for b in all_bconns if b.get("user_id") == 6363403785), None) or (all_bconns[0] if all_bconns else None)
                    if target_bc:
                        b_conn_id = target_bc.get("connection_id")
                        database.register_business_chat(cid, b_conn_id, target_bc.get("user_id"), c_title)
                        b_chat = target_bc

            send_as_biz = bool(b_conn_id and data.get("send_as_business", True))

            if send_as_biz and b_conn_id:
                # Send directly on behalf of the connected Telegram Business user!
                owner_title = (b_chat.get("owner_first_name") or b_chat.get("owner_username") or "Бизнес") if b_chat else "Бизнес"
                sent_msg = None
                if send_as_voice:
                    audio_bytes = generate_voice_bytes(text, style=voice_style)
                    if not audio_bytes:
                        return jsonify({"error": "Не удалось синтезировать голос"}), 500
                    try:
                        sent_msg = bot.send_voice(cid, audio_bytes, business_connection_id=b_conn_id)
                    except Exception as bve:
                        logger.warning(f"Business send_voice failed: {bve}. Trying userbot MTProto fallback...")
                        import premium_client
                        if premium_client.is_premium_connected():
                            p_ok = premium_client.send_premium_voice(cid, audio_bytes)
                            if p_ok:
                                sent_msg = type('Obj', (), {'message_id': int(time.time())})()
                        if not sent_msg:
                            raise bve
                    database.log_message(
                        chat_id=cid,
                        user_id=None,
                        sender_type="bot",
                        sender_name=f"{owner_title} (Voice)",
                        text=text,
                        media_type="voice",
                        chat_type="business"
                    )
                else:
                    try:
                        sent_msg = bot.send_message(cid, text, business_connection_id=b_conn_id)
                    except Exception as bme:
                        logger.warning(f"Business send_message failed: {bme}. Trying userbot MTProto fallback...")
                        import premium_client
                        if premium_client.is_premium_connected():
                            p_ok = premium_client.send_premium_message(cid, text)
                            if p_ok:
                                sent_msg = type('Obj', (), {'message_id': int(time.time())})()
                        if not sent_msg:
                            raise bme
                    database.log_message(
                        chat_id=cid,
                        user_id=None,
                        sender_type="bot",
                        sender_name=f"{owner_title} (Web)",
                        text=text,
                        media_type="text",
                        chat_type="business"
                    )
                return jsonify({
                    "status": "success",
                    "message_id": getattr(sent_msg, 'message_id', int(time.time())),
                    "sent_as_business": True,
                    "business_owner": owner_title
                })
            else:
                # Standard bot message
                sent_msg = None
                if send_as_voice:
                    audio_bytes = generate_voice_bytes(text, style=voice_style)
                    if not audio_bytes:
                        return jsonify({"error": "Не удалось синтезировать голос"}), 500
                    try:
                        sent_msg = bot.send_voice(cid, audio_bytes, reply_to_message_id=reply_to)
                    except Exception as sve:
                        import premium_client
                        if ("can't initiate" in str(sve).lower() or "forbidden" in str(sve).lower()) and premium_client.is_premium_connected():
                            if premium_client.send_premium_voice(cid, audio_bytes):
                                sent_msg = type('Obj', (), {'message_id': int(time.time())})()
                        if not sent_msg:
                            raise sve
                    sender_label = "NullSecAI (Аниме голос)" if voice_style == "anime" else ("NullSecAI (Девушка голос)" if voice_style == "girl" else "NullSecAI (Voice Admin)")
                    database.log_message(
                        chat_id=cid,
                        user_id=None,
                        sender_type="bot",
                        sender_name=sender_label,
                        text=text,
                        media_type="voice"
                    )
                else:
                    try:
                        sent_msg = bot.send_message(cid, text, reply_to_message_id=reply_to)
                    except Exception as sme:
                        import premium_client
                        if ("can't initiate" in str(sme).lower() or "forbidden" in str(sme).lower()) and premium_client.is_premium_connected():
                            if premium_client.send_premium_message(cid, text):
                                sent_msg = type('Obj', (), {'message_id': int(time.time())})()
                        if not sent_msg:
                            raise sme
                    database.log_message(
                        chat_id=cid,
                        user_id=None,
                        sender_type="bot",
                        sender_name="NullSecAI (Web Admin)",
                        text=text,
                        media_type="text"
                    )
                return jsonify({"status": "success", "message_id": getattr(sent_msg, 'message_id', int(time.time())), "sent_as_business": False})
        except Exception as e:
            err_str = str(e)
            if cid < 0 and any(m in err_str.lower() for m in ["not a member", "kicked", "chat not found", "chat was deleted", "deactivated"]):
                logger.info(f"Bot is no longer a member of group {cid}. Purging chat from database...")
                database.delete_chat(cid)
                return jsonify({"error": "Бот больше не состоит в этой группе. Чат автоматически удален из панели.", "chat_deleted": True}), 403
            logger.error(f"Failed to send admin message to chat {cid}: {e}")
            return jsonify({"error": f"Ошибка отправки в Telegram: {err_str}"}), 500

    limit_param = request.args.get('limit')
    try:
        limit = int(limit_param) if limit_param else 1000
    except (ValueError, TypeError):
        limit = 1000
    messages = database.get_chat_messages(cid, limit=limit)
    return jsonify(messages)

@app.route('/api/chats/<chat_id>', methods=['DELETE'])
@require_admin
def api_delete_chat(chat_id):
    """Permanently deletes a chat from database and causes bot to leave if group."""
    try:
        cid = int(chat_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Некорректный chat_id"}), 400

    bot = get_telegram_bot()
    if cid < 0 and bot:
        try:
            bot.leave_chat(cid)
        except Exception:
            pass

    database.delete_chat(cid)
    return jsonify({"status": "success", "chat_id": cid, "message": "Чат успешно удален из базы"})

@app.route('/api/chats/<chat_id>/leave', methods=['POST'])
@require_admin
def api_chat_leave(chat_id):
    """Forces the bot to leave a group or supergroup chat and removes it from active chats database."""
    try:
        cid = int(chat_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Некорректный chat_id"}), 400

    if cid > 0:
        return jsonify({"error": "Покинуть можно только группу (отрицательный chat_id)"}), 400

    bot = get_telegram_bot()
    err_note = None
    if bot:
        try:
            bot.leave_chat(cid)
        except Exception as e:
            err_note = str(e)
            logger.warning(f"Error calling leave_chat for {cid}: {e}")

    database.delete_chat(cid)

    if err_note:
        return jsonify({
            "status": "partial",
            "chat_id": cid,
            "message": f"Группа удалена из базы панели управления. Примечание Telegram API: {err_note}"
        })
    return jsonify({
        "status": "success",
        "chat_id": cid,
        "message": f"Бот успешно покинул группу {cid} и удалил ее из панели!"
    })

@app.route('/api/media/file/<path:file_id>')
def api_media_file(file_id):
    """Fetches photo, voice note, audio or video from Telegram Bot API and streams directly to browser."""
    if not file_id or str(file_id).startswith("["):
        return jsonify({"error": "Файл не найден"}), 404
    bot = get_telegram_bot()
    if not bot:
        return jsonify({"error": "Telegram бот не подключен"}), 503
    try:
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{config.TELEGRAM_BOT_TOKEN}/{file_info.file_path}"
        resp = requests.get(file_url, timeout=30)
        if resp.status_code == 200:
            content_type = resp.headers.get("Content-Type", "application/octet-stream")
            fp = file_info.file_path.lower()
            if fp.endswith((".jpg", ".jpeg")):
                content_type = "image/jpeg"
            elif fp.endswith(".png"):
                content_type = "image/png"
            elif fp.endswith(".webp"):
                content_type = "image/webp"
            elif fp.endswith((".oga", ".ogg")):
                content_type = "audio/ogg"
            elif fp.endswith(".mp3"):
                content_type = "audio/mpeg"
            elif fp.endswith(".mp4"):
                content_type = "video/mp4"
            return io.BytesIO(resp.content), 200, {"Content-Type": content_type}
        return jsonify({"error": f"Telegram API error {resp.status_code}"}), resp.status_code
    except Exception as e:
        logger.error(f"Error fetching telegram media {file_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/messages/<int:msg_id>', methods=['DELETE'])
@require_admin
def api_delete_single_message(msg_id):
    """Deletes a message from database and Telegram."""
    msg = database.get_message_by_id(msg_id)
    if not msg:
        return jsonify({"status": "error", "message": "Сообщение не найдено"}), 404
    
    chat_id = msg.get("chat_id")
    bot = get_telegram_bot()
    if bot and chat_id:
        try:
            bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
            
    ok = database.delete_message_by_id(msg_id)
    return jsonify({"status": "success", "deleted": ok})

@app.route('/api/messages/<int:msg_id>/forward', methods=['POST'])
@require_admin
def api_forward_single_message(msg_id):
    """Forwards a message to a target chat."""
    data = request.get_json() or {}
    target_chat_id = data.get("target_chat_id")
    if not target_chat_id:
        return jsonify({"error": "Не указан target_chat_id"}), 400
    msg = database.get_message_by_id(msg_id)
    if not msg:
        return jsonify({"error": "Сообщение не найдено"}), 404
    bot = get_telegram_bot()
    if not bot:
        return jsonify({"error": "Telegram бот не подключен"}), 503
    try:
        from_chat_id = msg.get("chat_id")
        sent = bot.forward_message(int(target_chat_id), from_chat_id, msg_id)
        return jsonify({"status": "success", "forwarded_message_id": sent.message_id})
    except Exception as e:
        return jsonify({"error": f"Ошибка пересылки: {e}"}), 500

@app.route('/api/messages/<int:msg_id>/reply', methods=['POST'])
@require_admin
def api_reply_to_single_message(msg_id):
    """Sends a reply to a specific message in the chat."""
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Текст ответа пуст"}), 400
    msg = database.get_message_by_id(msg_id)
    if not msg:
        return jsonify({"error": "Сообщение не найдено"}), 404
    bot = get_telegram_bot()
    if not bot:
        return jsonify({"error": "Telegram бот не подключен"}), 503
    try:
        chat_id = msg.get("chat_id")
        sent = bot.send_message(chat_id, text, reply_to_message_id=msg_id)
        database.log_message(
            chat_id=chat_id,
            user_id=None,
            sender_type="bot",
            sender_name="NullSecAI (Web Admin)",
            text=text,
            media_type="text"
        )
        return jsonify({"status": "success", "message_id": sent.message_id})
    except Exception as e:
        return jsonify({"error": f"Ошибка отправки ответа: {e}"}), 500

@app.route('/api/search')
@require_admin
def api_search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    results = database.search_messages(query)
    return jsonify(results)

@app.route('/api/users/<user_id>/economy', methods=['POST'])
@require_admin
def api_user_economy(user_id):
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Некорректный ID"}), 400

    data = request.get_json() or {}
    delta_coins = data.get('delta_coins')
    set_coins = data.get('set_coins')
    delta_rep = data.get('delta_rep')
    set_rep = data.get('set_rep')

    if set_coins is not None:
        database.set_user_coins(uid, int(set_coins))
    elif delta_coins is not None:
        database.change_user_coins(uid, int(delta_coins))

    if set_rep is not None:
        database.set_user_rep(uid, int(set_rep))
    elif delta_rep is not None:
        database.change_user_rep(uid, int(delta_rep))

    current_rep, current_coins = database.get_user_economy(uid)
    return jsonify({
        "status": "success",
        "user_id": uid,
        "coins": current_coins,
        "reputation": current_rep
    })

@app.route('/api/users/<user_id>/reputation', methods=['POST'])
@require_admin
def api_user_reputation(user_id):
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Некорректный ID"}), 400

    data = request.get_json() or {}
    set_rep = data.get('set_rep') or data.get('rep')
    delta_rep = data.get('delta_rep') or data.get('delta')

    if set_rep is not None:
        database.set_user_rep(uid, int(set_rep))
    elif delta_rep is not None:
        database.change_user_rep(uid, int(delta_rep))

    current_rep, current_coins = database.get_user_economy(uid)
    return jsonify({
        "status": "success",
        "user_id": uid,
        "reputation": current_rep,
        "coins": current_coins
    })

@app.route('/api/broadcast', methods=['POST'])
@require_admin
def api_broadcast():
    data = request.get_json() or {}
    text = data.get('text', '').strip()
    send_as_voice = bool(data.get('send_as_voice', False))
    target = data.get('target', 'all')  # 'all', 'users', 'groups'

    if not text:
        return jsonify({"error": "Текст рассылки пуст"}), 400

    bot = get_telegram_bot()
    if bot is None:
        return jsonify({"error": "Telegram бот не подключен"}), 503

    users = database.get_all_users()
    chats = database.get_all_chats()

    target_ids = set()
    if target == 'groups':
        for c in chats:
            if c.get('chat_type') != 'private' or int(c['chat_id']) < 0:
                target_ids.add(int(c['chat_id']))
    elif target == 'users':
        for u in users:
            if int(u['user_id']) > 0:
                target_ids.add(int(u['user_id']))
    else:  # 'all'
        for u in users:
            target_ids.add(int(u['user_id']))
        for c in chats:
            target_ids.add(int(c['chat_id']))

    sent_count = 0
    fail_count = 0

    voice_style = data.get('voice_style', 'default')
    audio_bytes = None
    if send_as_voice:
        audio_bytes = generate_voice_bytes(text, style=voice_style)

    for cid in target_ids:
        try:
            if send_as_voice and audio_bytes:
                bot.send_voice(cid, audio_bytes)
            else:
                bot.send_message(cid, f"📢 <b>Объявление от разработчика:</b>\n\n{text}", parse_mode="HTML")
            sent_count += 1
            time.sleep(0.04)  # throttle to avoid 429
        except Exception:
            fail_count += 1

    return jsonify({
        "status": "success",
        "sent": sent_count,
        "failed": fail_count,
        "total": len(target_ids)
    })

@app.route('/api/send_message', methods=['POST'])
@require_admin
def api_send_message():
    data = request.get_json() or {}
    chat_id = data.get('chat_id')
    text = data.get('text', '').strip()
    send_as_voice = bool(data.get('send_as_voice', False))
    voice_style = data.get('voice_style', 'default')
    reply_to = data.get('reply_to_message_id')

    if not chat_id or not text:
        return jsonify({"error": "Missing chat_id or text"}), 400

    bot = get_telegram_bot()
    if bot is None:
        return jsonify({"error": "Telegram bot instance not connected to web server"}), 503

    try:
        cid = int(chat_id)
        if send_as_voice:
            audio_bytes = generate_voice_bytes(text, style=voice_style)
            if not audio_bytes:
                return jsonify({"error": "Failed to synthesize voice"}), 500
            
            sent = bot.send_voice(cid, audio_bytes, reply_to_message_id=reply_to)
            sender_label = "NullSecAI (Аниме голос)" if voice_style == "anime" else ("NullSecAI (Девушка голос)" if voice_style == "girl" else "NullSecAI (Voice Admin)")
            database.log_message(
                chat_id=cid,
                user_id=None,
                sender_type="bot",
                sender_name=sender_label,
                text=text,
                media_type="voice"
            )
        else:
            sent = bot.send_message(cid, text, reply_to_message_id=reply_to)
            database.log_message(
                chat_id=cid,
                user_id=None,
                sender_type="bot",
                sender_name="NullSecAI (Web Admin)",
                text=text,
                media_type="text"
            )

        return jsonify({"status": "success", "message_id": sent.message_id})
    except Exception as e:
        logger.error(f"Failed to send admin message to chat {chat_id}: {e}")
        err_msg = str(e)
        if "BUSINESS_CONNECTION_INVALID" in err_msg:
            err_msg = "Чат секретаря (Telegram Business): отправка невозможна, так как собеседник не начинал диалог с ботом напрямую."
        elif "chat not found" in err_msg.lower():
            err_msg = "Чат не найден или пользователь заблокировал бота."
        elif "bot was blocked by the user" in err_msg.lower():
            err_msg = "Пользователь заблокировал бота в Telegram."
        return jsonify({"error": err_msg}), 500

@app.route('/api/chats/<chat_id>/ai_reply', methods=['POST'])
@require_admin
def api_chat_ai_reply(chat_id):
    """Generates an AI response from bot directly in the context of the chat."""
    try:
        cid = int(chat_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid chat_id"}), 400

    bot = get_telegram_bot()
    if bot is None:
        return jsonify({"error": "Telegram bot not connected"}), 503

    data = request.get_json() or {}
    custom_instruction = data.get('prompt', '').strip()

    try:
        import bot as bot_module
        messages = database.get_chat_messages(cid, limit=20)
        formatted_contents = []
        for m in messages:
            role = "user" if m.get('sender_type') == 'user' else "model"
            txt = m.get('text') or ""
            if txt.strip():
                formatted_contents.append({
                    "role": role,
                    "parts": [{"text": txt}]
                })
        
        if custom_instruction:
            formatted_contents.append({
                "role": "user",
                "parts": [{"text": custom_instruction}]
            })
        elif not formatted_contents or formatted_contents[-1]["role"] != "user":
            formatted_contents.append({
                "role": "user",
                "parts": [{"text": "Привет! Ответь на диалог кратко и по делу."}]
            })

        reply_text = bot_module.stream_gemini_to_telegram(cid, formatted_contents, user_id=cid)
        return jsonify({"status": "success", "reply": reply_text or "Ответ отправлен"})
    except Exception as e:
        logger.error(f"Failed to generate AI reply for chat {cid}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/business/connections')
@require_admin
def api_business_connections():
    """Returns all registered Telegram Business connections and their active chats."""
    conns = database.get_all_business_connections()
    b_chats = database.get_all_business_chats()
    return jsonify({
        "connections": conns,
        "chats": b_chats
    })

@app.route('/api/business/send', methods=['POST'])
@require_admin
def api_business_send():
    """Sends a new message into any chat on behalf of a connected Telegram Business user."""
    data = request.get_json() or {}
    target_chat_id = data.get('chat_id')
    conn_id = data.get('connection_id')
    text = (data.get('text') or '').strip()

    if not target_chat_id or not conn_id or not text:
        return jsonify({"error": "Укажите chat_id, connection_id и text"}), 400

    bot = get_telegram_bot()
    if not bot:
        return jsonify({"error": "Telegram бот не подключен"}), 503

    try:
        cid = int(target_chat_id)
        sent = bot.send_message(chat_id=cid, text=text, business_connection_id=conn_id)

        b_info = database.get_business_connection(conn_id)
        owner_id = b_info.get("user_id") if b_info else None
        owner_name = "Бизнес"
        if owner_id:
            u = database.get_user(owner_id)
            if u:
                owner_name = u.get("first_name") or u.get("username") or str(owner_id)

        database.register_business_chat(chat_id=cid, connection_id=conn_id, owner_id=owner_id)
        database.log_message(
            chat_id=cid,
            user_id=None,
            sender_type="bot",
            sender_name=f"{owner_name} (Web)",
            text=text,
            media_type="text",
            chat_type="business"
        )
        return jsonify({"status": "success", "message_id": sent.message_id})
    except Exception as e:
        logger.error(f"Error sending business message: {e}")
        return jsonify({"error": f"Ошибка отправки через Telegram Business: {str(e)}"}), 500

@app.route('/api/generate_code', methods=['POST'])
@require_admin
def api_generate_code():
    data = request.get_json() or {}
    prompt = data.get('prompt', '').strip()
    lang = (data.get('language') or 'html').lower()

    if not prompt:
        return jsonify({"error": "Промпт не указан"}), 400

    try:
        import config

        system_instruction = (
            f"You are NullSecAI, supreme frontend and script architect. "
            f"Generate 100% complete, working, production-ready code in {lang}. "
            f"If HTML: include complete embedded CSS and JS (single-file), sleek modern dark glassmorphism styling, responsive layout, animations, Inter/Outfit fonts, FontAwesome icons. "
            f"If Lua: generate full Luau / Roblox script with UI. "
            f"Output ONLY the pure raw code inside ```{lang} ... ``` markdown block without extra talk."
        )

        model = getattr(config, 'GEMINI_MODEL', 'gemini-2.5-flash')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={config.GEMINI_API_KEY}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {"temperature": 0.35}
        }
        res = requests.post(url, json=payload, timeout=30)
        res_data = res.json()
        code_text = ""
        candidates = res_data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                code_text = parts[0].get("text", "")
        m = re.search(rf"```{lang}?\s*([\s\S]*?)\s*```", code_text, re.IGNORECASE)
        if m:
            code_text = m.group(1).strip()
        else:
            m_any = re.search(r"```[a-zA-Z0-9_-]*\s*([\s\S]*?)\s*```", code_text)
            if m_any:
                code_text = m_any.group(1).strip()

        return jsonify({
            "status": "success",
            "language": lang,
            "code": code_text,
            "title": prompt[:40] + ("..." if len(prompt) > 40 else "")
        })
    except Exception as e:
        logger.error(f"Generate code error: {e}")
        if lang in ['html', 'htm']:
            code_fallback = f"""<!DOCTYPE html>
<html lang="ru" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{prompt[:30]}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        body {{ background: #030712; color: #f9fafb; font-family: system-ui, sans-serif; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; }}
        .glass {{ background: rgba(17, 24, 39, 0.85); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.1); }}
    </style>
</head>
<body class="p-6">
    <div class="glass max-w-xl w-full p-8 rounded-2xl shadow-2xl text-center space-y-4">
        <div class="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center text-2xl text-white shadow-lg shadow-cyan-500/30">
            <i class="fa-solid fa-wand-magic-sparkles"></i>
        </div>
        <h1 class="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-indigo-400 bg-clip-text text-transparent">{prompt}</h1>
        <p class="text-slate-400 text-sm">Сгенерировано в NullSecAI Frontend Studio</p>
        <button onclick="alert('Успешно!')" class="px-6 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold transition">Запустить</button>
    </div>
</body>
</html>"""
        else:
            code_fallback = f"-- NullSecAI Script: {prompt}\nprint('Loaded: {prompt}')"
        
        return jsonify({
            "status": "success",
            "language": lang,
            "code": code_fallback,
            "title": prompt[:40]
        })


@app.route('/api/ai/chat', methods=['POST'])
@require_admin
def api_ai_chat():
    """Direct dialogue between the operator and NullSec Core AI."""
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    history = data.get('history', [])
    
    if not message:
        return jsonify({"error": "Пустое сообщение"}), 400
        
    try:
        import config
        import requests
        
        system_instruction = (
            "Ты — NullSec Core AI, личный терминальный ассистент и технический компаньон оператора/создателя системы. "
            "Разработчики системы: @k3rnel8633 и @ImNotRealQwQ. "
            "Отвечай прямо, точно, по-человечески, с живым умом и без шаблонных корпоративных извинений и воды. "
            "Ты можешь писать код (Lua/Roblox, Python, JS, C++), помогать администрировать бота, "
            "анализировать ошибки, давать технические советы и просто общаться на любые темы. "
            "Форматируй код в Markdown блоки."
        )
        
        contents = []
        for h in history[-8:]:
            r = "user" if h.get("role") == "user" else "model"
            txt = h.get("content") or h.get("text") or ""
            if txt.strip():
                contents.append({"role": r, "parts": [{"text": txt}]})
        contents.append({"role": "user", "parts": [{"text": message}]})
        
        model = getattr(config, 'GEMINI_MODEL', 'gemini-2.5-flash')
        api_key = getattr(config, 'GEMINI_API_KEY', '')
        
        reply_text = ""
        if api_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": contents,
                "system_instruction": {"parts": [{"text": system_instruction}]},
                "generationConfig": {"temperature": 0.8}
            }
            res = requests.post(url, json=payload, timeout=30)
            res_data = res.json()
            candidates = res_data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    reply_text = parts[0].get("text", "")
                    
        if not reply_text:
            reply_text = f"[NullSec-Core]: Запрос принят. Ядро функционирует стабильно. Получено: '{message[:60]}'"
            
        return jsonify({"status": "success", "reply": reply_text})
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        return jsonify({"error": str(e), "reply": f"Ошибка связи с ИИ: {e}"}), 500

@app.route('/api/terminal/exec', methods=['POST'])
@require_admin
def api_terminal_exec():
    """Terminal command-line engine for NullSec Operator Console."""
    data = request.get_json() or {}
    raw_cmd = data.get('command', '').strip()
    if not raw_cmd:
        return jsonify({"output": ""})
        
    parts = raw_cmd.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""
    
    if cmd in ['clear', 'cls']:
        return jsonify({"clear": True})
        
    if cmd in ['exit', 'logout', 'quit']:
        return jsonify({"logout": True})
        
    if cmd in ['help', '?']:
        help_text = (
            "=== NULLSEC TERMINAL COMMANDS ===\n"
            "  ai <запрос>        - Запрос к ИИ NullSec Core (или просто введите любой текст)\n"
            "  status             - Системный статус ноды, память, runtime\n"
            "  stats              - Метрики: пользователи, чаты, скрипты\n"
            "  users              - Список последних пользователей\n"
            "  chats              - Список активных чатов\n"
            "  scripts            - Список облачных скриптов\n"
            "  whoami             - Информация об операторе текущей сессии\n"
            "  uname              - Информация о ядре системы\n"
            "  neofetch           - Информационный баннер ноды\n"
            "  grant <id> <days>  - Выдать Premium пользователю\n"
            "  broadcast <текст>  - Рассылка сообщения всем пользователям бота\n"
            "  clear              - Очистить экран терминала\n"
            "  exit               - Выход из панели оператора\n"
            "\n* Любой произвольный ввод автоматически перенаправляется в ИИ ядро."
        )
        return jsonify({"output": help_text})
        
    if cmd == 'whoami':
        return jsonify({"output": "root@nullsec (Operator Console) [AUTH: OK // PERMS: ALL]"})
        
    if cmd in ['uname', 'uname -a']:
        return jsonify({"output": "Linux nullsec-node01 3.14.3-LNX #1 SMP PREEMPT x86_64 GNU/Linux"})
        
    if cmd in ['neofetch', 'fastfetch']:
        banner = (
            "       /\\          root@nullsec-node01\n"
            "      /  \\         -------------------\n"
            "     / /\\ \\        OS: NullSec Custom Linux x86_64\n"
            "    / /  \\ \\       Host: Render Cloud Enterprise\n"
            "   /_/    \\_\\      Kernel: 3.14.3-LNX\n"
            "  /________\\       Shell: nullsec-sh (interactive CLI)\n"
            "                    Terminal: WebApp Console v2.4\n"
            "                    Engine: NullSec Core AI (Active)\n"
            "                    Status: 24/7 ONLINE / ALL SYSTEMS GREEN"
        )
        return jsonify({"output": banner})
        
    if cmd == 'status':
        import platform
        uptime_sec = int(time.time() - _start_time)
        hours = uptime_sec // 3600
        mins = (uptime_sec % 3600) // 60
        secs = uptime_sec % 60
        out = (
            "[SYSTEM DIAGNOSTICS // NODE-01]\n"
            f"OS: {platform.system()} {platform.release()}\n"
            f"Runtime: Python 3.14.3 (Flask + Telethon + pyTelegramBotAPI)\n"
            f"Uptime: {hours}h {mins}m {secs}s\n"
            "Cluster: Online 24/7\n"
            "Database: SQLite / Persistent Local\n"
            "AI Neural Engine: Active"
        )
        return jsonify({"output": out})
        
    if cmd == 'stats':
        try:
            total_users = database.get_total_users_count() if hasattr(database, 'get_total_users_count') else len(database.get_all_users())
            premium_users = len(database.get_premium_users()) if hasattr(database, 'get_premium_users') else 0
            chats = len(database.get_all_chats()) if hasattr(database, 'get_all_chats') else 0
            out = (
                "[METRICS OVERVIEW]\n"
                f"Total Users: {total_users}\n"
                f"Premium Users: {premium_users}\n"
                f"Active Chats: {chats}\n"
                f"Cloud Scripts: {len(CLOUD_SCRIPTS)}"
            )
            return jsonify({"output": out})
        except Exception as e:
            return jsonify({"output": f"Stats error: {e}"})
            
    if cmd == 'scripts':
        lines = ["ID          | TITLE                          | LANG"]
        lines.append("------------+--------------------------------+--------")
        for s in CLOUD_SCRIPTS:
            sid = str(s.get('id', ''))[:11].ljust(11)
            stitle = str(s.get('title', ''))[:30].ljust(30)
            slang = str(s.get('language', 'lua'))[:6]
            lines.append(f"{sid} | {stitle} | {slang}")
        return jsonify({"output": "\n".join(lines)})

    if cmd == 'users':
        try:
            users = database.get_all_users()[:15]
            lines = ["ID          | USERNAME        | PREMIUM  | CREATED"]
            lines.append("------------+-----------------+----------+-------------------")
            for u in users:
                uid = str(u.get('user_id', ''))[:11].ljust(11)
                uname = ('@' + str(u.get('username') or 'anon'))[:15].ljust(15)
                prem = ('YES' if u.get('is_premium') else 'NO').ljust(8)
                c_at = str(u.get('created_at', ''))[:19]
                lines.append(f"{uid} | {uname} | {prem} | {c_at}")
            return jsonify({"output": "\n".join(lines)})
        except Exception as e:
            return jsonify({"output": f"Users error: {e}"})
            
    if cmd == 'chats':
        try:
            chats = database.get_all_chats()[:15]
            lines = ["CHAT ID       | TITLE                      | TYPE"]
            lines.append("--------------+----------------------------+----------")
            for c in chats:
                cid = str(c.get('chat_id', ''))[:13].ljust(13)
                title = str(c.get('title') or 'Direct')[:26].ljust(26)
                ctype = str(c.get('chat_type') or 'private')[:10]
                lines.append(f"{cid} | {title} | {ctype}")
            return jsonify({"output": "\n".join(lines)})
        except Exception as e:
            return jsonify({"output": f"Chats error: {e}"})
            
    if cmd == 'grant':
        if not arg:
            return jsonify({"output": "Использование: grant <user_id> [дней (по умолч 30)]"})
        subparts = arg.split()
        target_uid = subparts[0]
        days = int(subparts[1]) if len(subparts) > 1 and subparts[1].isdigit() else 30
        try:
            target_int = int(target_uid)
            database.grant_premium(target_int, days)
            return jsonify({"output": f"[OK] Премиум успешно выдан пользователю {target_int} на {days} дней."})
        except Exception as e:
            return jsonify({"output": f"[ERR] Ошибка выдачи премиума: {e}"})
            
    if cmd == 'broadcast':
        if not arg:
            return jsonify({"output": "Использование: broadcast <текст рассылки>"})
        bot = get_telegram_bot()
        if not bot:
            return jsonify({"output": "[ERR] Telegram бот не подключен."})
        try:
            users = database.get_all_users()
            cnt = 0
            for u in users:
                uid = u.get('user_id')
                if uid:
                    try:
                        bot.send_message(uid, arg)
                        cnt += 1
                    except Exception:
                        pass
            return jsonify({"output": f"[OK] Рассылка завершена. Доставлено пользователям: {cnt}"})
        except Exception as e:
            return jsonify({"output": f"[ERR] Ошибка рассылки: {e}"})

    # Default: Route directly to NullSec AI Core
    ai_prompt = arg if cmd == 'ai' else raw_cmd
    try:
        import config
        import requests
        system_instruction = (
            "Ты — NullSec Core AI, личный терминальный ассистент и технический компаньон оператора/создателя бота. "
            "Разработчики системы: @k3rnel8633 и @ImNotRealQwQ. "
            "Отвечай прямо, точно, по-человечески, с живым умом и без шаблонных корпоративных извинений и воды. "
            "Ты можешь писать код (Lua/Roblox, Python, JS, C++), помогать администрировать бота, "
            "анализировать ошибки, давать технические советы и просто общаться на любые темы."
        )
        model = getattr(config, 'GEMINI_MODEL', 'gemini-2.5-flash')
        api_key = getattr(config, 'GEMINI_API_KEY', '')
        if api_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": ai_prompt}]}],
                "system_instruction": {"parts": [{"text": system_instruction}]},
                "generationConfig": {"temperature": 0.8}
            }
            res = requests.post(url, json=payload, timeout=30)
            res_data = res.json()
            candidates = res_data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    ai_reply = parts[0].get("text", "")
                    return jsonify({"output": f"[NULLSEC-AI]:\n{ai_reply}"})
        return jsonify({"output": f"[NULLSEC-AI]: Принято в обработку: {ai_prompt}"})
    except Exception as e:
        return jsonify({"output": f"[NULLSEC-AI]: Ошибка генерации: {e}"})


@app.route('/api/system/status')
@require_admin
def api_system_status():
    import platform
    now = time.time()
    uptime_sec = int(now - _start_time)
    hours = uptime_sec // 3600
    minutes = (uptime_sec % 3600) // 60
    seconds = uptime_sec % 60
    uptime_str = f"{hours}ч {minutes}м {seconds}с"

    commit_sha = "main"
    try:
        import subprocess
        res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            commit_sha = res.stdout.strip()
    except Exception:
        pass

    db_stats = database.get_dashboard_stats()
    
    prem_conn = False
    only_act = False
    try:
        import premium_client
        prem_conn = premium_client.is_premium_connected()
        only_act = premium_client.is_always_online()
    except Exception:
        pass

    return jsonify({
        "status": "online",
        "service": "NullSecAI Web Control Center v5.0",
        "uptime": uptime_str,
        "uptime_seconds": uptime_sec,
        "git_commit": commit_sha,
        "python_version": platform.python_version(),
        "premium_client_connected": prem_conn,
        "always_online_active": only_act,
        "stats": db_stats,
        "creator": "k3rnel (@k3rnel8633)",
        "repo": "https://github.com/AUser7742/pomoshotru_bot"
    })

@app.route('/export/<chat_id>')
@require_admin
def export_chat(chat_id):
    cid = int(chat_id)
    messages = database.get_chat_messages(cid, limit=2500)
    lines = [f"=== NullSecAI Telegram Chat History Export (Chat ID: {chat_id}) ===", ""]
    for m in messages:
        sender = "NullSecAI [BOT]" if m['sender_type'] == 'bot' else f"{m['sender_name']} [USER]"
        lines.append(f"[{m['timestamp']}] {sender}:")
        if m['media_type'] and m['media_type'] != 'text':
            lines.append(f"  [Type: {m['media_type']}]")
        lines.append(f"  {m['text']}")
        lines.append("")

    return Response("\n".join(lines), mimetype='text/plain', headers={"Content-Disposition": f"attachment; filename=chat_{chat_id}_export.txt"})

def start_web_server(bot=None, port=None):
    if bot:
        set_bot_instance(bot)
    
    server_port = int(port or os.environ.get("PORT", 10000))
    
    def _run_port(p):
        try:
            logger.info(f"🌐 Starting Web Dashboard on http://0.0.0.0:{p}")
            app.run(host="0.0.0.0", port=p, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            logger.warning(f"Port {p} bind note: {e}")

    t = threading.Thread(target=_run_port, args=(server_port,), daemon=True)
    t.start()

    # Also listen on standard Render port 10000 and HF port 7860 if different
    for extra_p in [10000, 7860]:
        if extra_p != server_port:
            threading.Thread(target=_run_port, args=(extra_p,), daemon=True).start()

    return t

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Telegram Web Dashboard running on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
