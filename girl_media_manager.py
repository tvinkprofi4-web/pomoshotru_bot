import os
import random
import logging
import math
import io
import asyncio
import subprocess
try:
    import numpy as np
    from PIL import Image
except ImportError:
    np = None
    Image = None

try:
    import imageio
    import imageio_ffmpeg
except ImportError:
    imageio = None
    imageio_ffmpeg = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR, "assets", "girl_media")
PHOTOS_DIR = os.path.join(MEDIA_DIR, "photos")
CIRCLES_DIR = os.path.join(MEDIA_DIR, "circles")

PHOTO_CAPTIONS = [
    "лови фото) как тебе мой лук? 😘",
    "ща еще скину, только не смейся 🙈",
    "специально для тебя сфоткалась) понравилось?) ✨",
    "вот так я сейчас выгляжу) как настроение? 😉",
    "а я кое-что интересное хотела скинуть) лови фото 😘",
    "держи селфи) только никому не показывай 🙈✨",
    "хехехе, лови) как тебе фигура?) 😘💅",
    "смотри какое фото получилось ✨ как тебе? 😉",
    "лови фотку) чем сейчас занят? 😉",
    "сделала селфи для тебя) оцени от 1 до 10? 😘"
]

CIRCLE_CAPTIONS = [
    "держи кружочек 😘 только никому не показывай)",
    "записала тебе кружок ✨ как ты там?)",
    "лови кружочек) соскучилась немного 🙈",
    "хехе, записала на секунду) как тебе? 😘",
    "держи кругляш ✨ чем вечером планируешь заняться? 😉",
    "лови видеокружок) слушай со звуком 😘"
]

VOICE_SCRIPTS = [
    "Привет! Записала тебе кружочек, как твои дела? 😘",
    "Смотри, какой кружочек я для тебя записала) Чем сейчас занят? ✨",
    "Хехе, держи кругляш! Соскучилась немного, решила записать видео 🙈",
    "Привет! Лови кружочек от меня, как настроение? 😉",
    "Специально для тебя сняла кругляш) Понравилось? 😘",
    "Привет! Чем занимаешься? Лови кружочек от меня ✨"
]

def get_girl_photo():
    """
    Returns (photo_bytes_io, caption) or (None, None)
    """
    if not os.path.exists(PHOTOS_DIR):
        return None, None
    
    valid_exts = ('.jpg', '.jpeg', '.png', '.webp')
    photos = [
        os.path.join(PHOTOS_DIR, f) for f in os.listdir(PHOTOS_DIR)
        if f.lower().endswith(valid_exts) and not f.startswith('circle_')
    ]
    
    if not photos:
        return None, None
    
    chosen = random.choice(photos)
    try:
        with open(chosen, "rb") as f:
            data = f.read()
        bio = io.BytesIO(data)
        bio.name = os.path.basename(chosen)
        caption = random.choice(PHOTO_CAPTIONS)
        return bio, caption
    except Exception as e:
        logger.error(f"Error reading girl photo {chosen}: {e}")
        return None, None

def generate_dynamic_video_note(voice_text=None, photo_path=None):
    """
    Generates a live, animated 1:1 square MP4 video note with realistic camera breathing and voice.
    """
    if not imageio or not imageio_ffmpeg:
        return None, None
        
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if not ffmpeg_exe:
            return None, None
            
        # 1. Select speech text
        text = voice_text or random.choice(VOICE_SCRIPTS)
        caption = random.choice(CIRCLE_CAPTIONS)
        
        # 2. Select photo
        if not photo_path or not os.path.exists(photo_path):
            valid_exts = ('.jpg', '.jpeg', '.png', '.webp')
            photos = [
                os.path.join(PHOTOS_DIR, f) for f in os.listdir(PHOTOS_DIR)
                if f.lower().endswith(valid_exts) and not f.startswith('circle_')
            ]
            if not photos:
                return None, None
            photo_path = random.choice(photos)
            
        temp_id = random.randint(10000, 99999)
        temp_mp3 = os.path.join(MEDIA_DIR, f"temp_voice_{temp_id}.mp3")
        temp_raw = os.path.join(MEDIA_DIR, f"temp_raw_{temp_id}.mp4")
        out_mp4 = os.path.join(MEDIA_DIR, f"temp_circle_{temp_id}.mp4")
        
        # 3. Generate voice with Edge TTS
        async def _gen_voice():
            comm = edge_tts.Communicate(text, voice='ru-RU-SvetlanaNeural', rate='+6%', pitch='+12Hz')
            await comm.save(temp_mp3)
            
        asyncio.run(_gen_voice())
        
        # 4. Probe duration
        probe_cmd = [ffmpeg_exe, '-i', temp_mp3]
        p = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration = 3.5
        for line in p.stderr.splitlines():
            if 'Duration:' in line:
                parts = line.split('Duration:')[1].split(',')[0].strip().split(':')
                duration = float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
                break
        duration = max(2.5, min(duration + 0.3, 8.0))
        
        # 5. Render animated square frames
        img = Image.open(photo_path).convert('RGB')
        w, h = img.size
        min_side = min(w, h)
        left = (w - min_side) // 2
        top = (h - min_side) // 4
        img_sq = img.crop((left, top, left + min_side, top + min_side)).resize((400, 400), Image.Resampling.LANCZOS)
        
        fps = 20
        num_frames = int(duration * fps)
        frames = []
        for i in range(num_frames):
            scale = 1.0 + 0.025 * math.sin(2 * math.pi * i / num_frames)
            shift_x = int(3 * math.sin(2 * math.pi * i / (num_frames / 2)))
            shift_y = int(2 * math.cos(2 * math.pi * i / (num_frames / 2)))
            cur_sz = int(400 * scale)
            t_img = img_sq.resize((cur_sz, cur_sz), Image.Resampling.BILINEAR)
            c_left = max(0, min(cur_sz - 400, (cur_sz - 400) // 2 + shift_x))
            c_top = max(0, min(cur_sz - 400, (cur_sz - 400) // 2 + shift_y))
            f_crop = t_img.crop((c_left, c_top, c_left + 400, c_top + 400))
            frames.append(np.array(f_crop))
            
        writer = imageio.get_writer(temp_raw, fps=fps, codec='libx264', pixelformat='yuv420p')
        for f in frames:
            writer.append_data(f)
        writer.close()
        
        # 6. Merge audio & video
        cmd = [
            ffmpeg_exe, '-y',
            '-i', temp_raw,
            '-i', temp_mp3,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-shortest',
            out_mp4
        ]
        subprocess.run(cmd, capture_output=True)
        
        with open(out_mp4, "rb") as f:
            v_data = f.read()
            
        for tmp in [temp_mp3, temp_raw, out_mp4]:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass
                    
        bio = io.BytesIO(v_data)
        bio.name = "circle.mp4"
        return bio, caption
    except Exception as e:
        logger.error(f"Error generating dynamic video note: {e}")
        return None, None

def get_girl_video_note():
    """
    Returns (video_note_bytes_io, caption) or (None, None)
    Uses pre-rendered high-quality circles library with dynamic generation fallback.
    """
    if os.path.exists(CIRCLES_DIR):
        videos = [
            os.path.join(CIRCLES_DIR, f) for f in os.listdir(CIRCLES_DIR)
            if f.lower().endswith(('.mp4', '.mov'))
        ]
        if videos:
            chosen = random.choice(videos)
            try:
                with open(chosen, "rb") as f:
                    data = f.read()
                bio = io.BytesIO(data)
                bio.name = os.path.basename(chosen)
                caption = random.choice(CIRCLE_CAPTIONS)
                return bio, caption
            except Exception as e:
                logger.error(f"Error reading girl video note {chosen}: {e}")
    
    # Fallback to dynamic generation
    return generate_dynamic_video_note()
