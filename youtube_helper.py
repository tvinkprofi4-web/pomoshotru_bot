import re
import os
import io
import time
import logging
import requests
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
import config

logger = logging.getLogger(__name__)

YOUTUBE_REGEX = re.compile(
    r'(https?://)?(www\.|m\.)?(youtube\.com/(?:watch\?v=|shorts/|embed/|live/|v/)|youtu\.be/)([a-zA-Z0-9_-]{11})',
    re.IGNORECASE
)

def extract_youtube_url(text):
    if not text:
        return None, None
    m = YOUTUBE_REGEX.search(text)
    if m:
        full_url = m.group(0)
        video_id = m.group(4)
        if not full_url.startswith('http'):
            full_url = 'https://' + full_url
        return full_url, video_id
    return None, None

def extract_video_id(url_or_id):
    if not url_or_id:
        return None
    if len(url_or_id) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id
    _, v_id = extract_youtube_url(url_or_id)
    return v_id

def format_duration(seconds):
    if not seconds:
        return '0:00'
    try:
        s = int(seconds)
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        if h > 0:
            return f'{h}:{m:02d}:{sec:02d}'
        return f'{m}:{sec:02d}'
    except Exception:
        return str(seconds)

def get_video_info(video_url_or_id):
    video_id = extract_video_id(video_url_or_id)
    if not video_id:
        return None
    
    url = f'https://www.youtube.com/watch?v={video_id}'
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None
            
            title = info.get('title') or 'YouTube Video'
            uploader = info.get('uploader') or info.get('channel') or 'Автор неизвестен'
            duration_sec = info.get('duration') or 0
            view_count = info.get('view_count') or 0
            like_count = info.get('like_count') or 0
            description = info.get('description') or ''
            thumbnail = info.get('thumbnail') or f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'
            tags = info.get('tags') or []
            upload_date = info.get('upload_date') or ''
            
            return {
                'video_id': video_id,
                'url': url,
                'title': title,
                'uploader': uploader,
                'duration_sec': duration_sec,
                'duration_str': format_duration(duration_sec),
                'view_count': view_count,
                'like_count': like_count,
                'description': description,
                'thumbnail': thumbnail,
                'tags': tags[:8],
                'upload_date': upload_date
            }
    except Exception as e:
        logger.warning(f'yt-dlp info error for {video_id}: {e}')
        # Fallback to basic oEmbed info
        try:
            oembed_url = f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json'
            resp = requests.get(oembed_url, timeout=5)
            if resp.status_code == 200:
                odata = resp.json()
                return {
                    'video_id': video_id,
                    'url': url,
                    'title': odata.get('title', 'YouTube Video'),
                    'uploader': odata.get('author_name', 'Автор'),
                    'duration_sec': 0,
                    'duration_str': 'Неизвестно',
                    'view_count': 0,
                    'like_count': 0,
                    'description': '',
                    'thumbnail': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
                    'tags': [],
                    'upload_date': ''
                }
        except Exception:
            pass
        return {
            'video_id': video_id,
            'url': url,
            'title': 'YouTube Video',
            'uploader': 'YouTube',
            'duration_sec': 0,
            'duration_str': 'Неизвестно',
            'view_count': 0,
            'like_count': 0,
            'description': '',
            'thumbnail': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
            'tags': [],
            'upload_date': ''
        }

def get_video_transcript(video_id_or_url):
    video_id = extract_video_id(video_id_or_url)
    if not video_id:
        return ''
        
    try:
        api = YouTubeTranscriptApi()
        # Try fetching in Russian, English, or whatever is available
        snippets = api.fetch(video_id, languages=['ru', 'en', 'uk', 'be', 'kk', 'ja', 'auto'])
        if snippets:
            lines = []
            for s in snippets:
                time_tag = format_duration(int(s.start))
                txt = s.text.replace('\n', ' ').strip()
                if txt:
                    lines.append(f'[{time_tag}] {txt}')
            return '\n'.join(lines)
    except Exception as e:
        logger.debug(f'TranscriptApi notice for {video_id}: {e}')
        
    return ''

def download_audio_bytes(video_id_or_url, max_duration_sec=1200):
    video_id = extract_video_id(video_id_or_url)
    if not video_id:
        return None, None
        
    url = f'https://www.youtube.com/watch?v={video_id}'
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_template = os.path.join(tmp_dir, '%(id)s.%(ext)s')
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'quiet': True,
            'no_warnings': True,
            'max_filesize': 50 * 1024 * 1024
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                dur = info.get('duration') or 0
                if dur > max_duration_sec:
                    return None, 'Видео слишком длинное для аудио-загрузки (максимум 20 мин).'
                
                files = os.listdir(tmp_dir)
                if not files:
                    return None, 'Файл не скачался'
                
                target_file = os.path.join(tmp_dir, files[0])
                with open(target_file, 'rb') as f:
                    audio_data = f.read()
                    
                title = info.get('title', 'audio')
                return audio_data, title
        except Exception as e:
            logger.warning(f'Audio download error: {e}')
            return None, str(e)

def get_available_video_formats(video_id_or_url):
    """
    Extracts available video quality options (1080p, 720p, 480p, 360p, MP3) with sizes.
    """
    video_id = extract_video_id(video_id_or_url)
    if not video_id:
        return None
    url = f'https://www.youtube.com/watch?v={video_id}'
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None
                
            formats = info.get('formats', [])
            dur_sec = info.get('duration') or 0
            title = info.get('title', 'YouTube Video')
            
            # Group available resolutions
            res_map = {}
            for f in formats:
                h = f.get('height')
                vcodec = f.get('vcodec', 'none')
                if h and vcodec != 'none' and h in [1080, 720, 480, 360, 240]:
                    filesize = f.get('filesize') or f.get('filesize_approx')
                    if not filesize and f.get('tbr') and dur_sec:
                        filesize = int(f.get('tbr') * 1024 * dur_sec / 8)
                    if h not in res_map or (filesize and filesize > (res_map[h].get('filesize') or 0)):
                        res_map[h] = {
                            'height': h,
                            'format_id': f.get('format_id'),
                            'ext': f.get('ext', 'mp4'),
                            'filesize': filesize
                        }
            
            sorted_res = sorted(res_map.keys(), reverse=True)
            result_list = []
            for h in sorted_res:
                item = res_map[h]
                size_mb = round(item['filesize'] / (1024 * 1024), 1) if item.get('filesize') else None
                fits_tg = (size_mb is None or size_mb <= 49.5)
                result_list.append({
                    'height': h,
                    'label': f"{h}p" + (f" (~{size_mb} MB)" if size_mb else ""),
                    'size_mb': size_mb,
                    'fits_telegram': fits_tg
                })
                
            return {
                'video_id': video_id,
                'title': title,
                'duration_sec': dur_sec,
                'qualities': result_list
            }
    except Exception as e:
        logger.warning(f'Error getting formats for {video_id}: {e}')
        return None

def download_video_tempfile(video_id_or_url, target_height=720, max_filesize_mb=50):
    """
    Downloads YouTube video at target resolution to an isolated temporary file,
    ensuring safe memory footprint on Render.
    Returns: (temp_filepath, title, duration, size_mb, width, height) or (None, err_msg)
    """
    video_id = extract_video_id(video_id_or_url)
    if not video_id:
        return None, "Некорректный ID видео", 0, 0, 0, 0
        
    url = f'https://www.youtube.com/watch?v={video_id}'
    import tempfile
    
    tmp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False, prefix=f"yt_{video_id}_{target_height}_")
    tmp_path = tmp_file.name
    tmp_file.close()
    
    # Best progressive MP4 or fast merge under target height
    ydl_opts = {
        'format': f'bestvideo[height<={target_height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={target_height}][ext=mp4]/best[height<={target_height}]/best',
        'outtmpl': tmp_path,
        'quiet': True,
        'no_warnings': True,
        'max_filesize': max_filesize_mb * 1024 * 1024,
        'overwrites': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'YouTube Video')
            dur = info.get('duration') or 0
            width = info.get('width') or 1280
            height = info.get('height') or target_height
            
            if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                # Try finding if yt-dlp added an extension like .mp4.mp4 or .mkv
                cand_dir = os.path.dirname(tmp_path)
                base_name = os.path.basename(tmp_path)
                found = False
                for f in os.listdir(cand_dir):
                    if f.startswith(base_name) and os.path.getsize(os.path.join(cand_dir, f)) > 0:
                        tmp_path = os.path.join(cand_dir, f)
                        found = True
                        break
                if not found:
                    return None, "Файл не сохранился на диск", 0, 0, 0, 0
                    
            size_mb = round(os.path.getsize(tmp_path) / (1024 * 1024), 2)
            if size_mb > max_filesize_mb:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                return None, f"Размер видео ({size_mb} MB) превышает лимит Telegram (50 MB). Выберите качество ниже (например 480p или 360p).", 0, 0, 0, 0
                
            return tmp_path, title, dur, size_mb, width, height
    except Exception as e:
        logger.warning(f"Video download error {video_id}: {e}")
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return None, str(e), 0, 0, 0, 0

def search_youtube_first_video(query):
    """Searches YouTube for the query and returns the top video information."""
    if not query:
        return None
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': True,
        'no_warnings': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(f'ytsearch1:{query}', download=False)
            entries = res.get('entries', [])
            if entries and len(entries) > 0:
                first_entry = entries[0]
                vid_id = first_entry.get('id') or first_entry.get('url')
                if vid_id:
                    return get_video_info(vid_id)
    except Exception as e:
        logger.warning(f'YouTube search error for "{query}": {e}')
    return None

def analyze_youtube_video(video_info, transcript_text=None, user_query=None, is_creator=False):
    """
    Uses Gemini AI to watch, summarize, extract key points/timestamps, and answer questions about the video.
    """
    if not video_info:
        return "⚠️ Не удалось получить информацию о видео."

    title = video_info.get("title", "YouTube Video")
    uploader = video_info.get("uploader", "Автор")
    duration = video_info.get("duration_str", "Неизвестно")
    views = video_info.get("view_count", 0)
    desc = video_info.get("description", "")
    if len(desc) > 3000:
        desc = desc[:3000] + "..."

    transcript_block = ""
    if transcript_text and transcript_text.strip():
        transcript_block = f"\n\n--- СУБТИТРЫ / ТРАНСКРИПТ ВИДЕО (С ТАЙМКОДАМИ) ---\n{transcript_text[:35000]}"
    else:
        transcript_block = f"\n\n--- ОПИСАНИЕ И ИНФОРМАЦИЯ О ВИДЕО (СУБТИТРЫ ОТСУТСТВУЮТ) ---\n{desc}"

    creator_note = "Общайся с k3rnel как с создателем и боссом." if is_creator else ""

    prompt = (
        f"Ты — AI for copil, самый умный ИИ-ассистент, созданный k3rnel. {creator_note}\n"
        f"Ты только что внимательно посмотрел и проанализировал следующее YouTube видео:\n\n"
        f"🎬 Название: {title}\n"
        f"👤 Канал / Автор: {uploader}\n"
        f"⏱ Длительность: {duration}\n"
        f"👁 Просмотров: {views:,}\n"
        f"{transcript_block}\n\n"
        f"Вопрос / запрос пользователя к видео: {user_query or 'Сделай полный разбор и саммари видео'}\n\n"
        "ЗАДАЧА:\n"
        "Составь четкий, структурированный, полезный и красивый анализ видео на русском языке.\n"
        "Формат ответа:\n"
        "1. 📌 **Главная суть:** Кратко в 2-3 предложениях объясни, о чём это видео и какова главная мысль.\n"
        "2. ⏱ **Ключевые моменты и таймкоды:** Если есть транскрипт или этапы — выдели 3-6 основных моментов с таймкодами [MM:SS] и краткой сутью.\n"
        "3. 💡 **Главные инсайты / тезисы:** Выдели 2-4 самых ценных вывода, факта или практических совета.\n"
        "4. ❓ **Ответ на вопрос:** (Если пользователь задал конкретный вопрос в запросе выше — дай исчерпывающий, точный ответ на него на основе содержания видео).\n\n"
        "Используй красивое оформление markdown и эмодзи. Говори по делу, без воды!"
    )

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
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
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                if text and len(text) > 20:
                    return text
        except Exception as e:
            logger.warning(f"Error calling Gemini {model} for YouTube analysis: {e}")
            continue

    # Fallback if API fails
    return f"🎬 **{title}** ({uploader}, {duration})\n\n{desc[:500]}"

