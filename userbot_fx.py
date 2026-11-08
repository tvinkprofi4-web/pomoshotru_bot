"""
userbot_fx.py
Comprehensive Userbot & Roleplay Engine for AI for copil
Includes:
- RP Actions (Romance, Care, Flirt, Aggression, 18+ & Trash) with automatic GIF animations
- TextFX Animation Engine (.type, _type, .scrlt, .shutter, .center, .corners, .blur, .drop, .radar_scan, .rain, .moon)
- Demotivator Meme Generator (.memez with Times New Roman & Pillow)
- Olbanskiy / Падонкаффский язык Converter (.dumb)
- Text Styler (.bold)
- Link Generator (.link)
- GIF Spammer (.spagif)
- Auto-Media Response System (.autovideo, .autofile, .autophoto, .autoround, .autosticker)
"""

import os
import sys
import io
import time
import random
import re
import html
import logging
import threading
import urllib.parse
import requests
from PIL import Image, ImageDraw, ImageFont
import telebot
from telebot import types

logger = logging.getLogger(__name__)

# =====================================================================
# 1. ROLEPLAY ACTIONS & GIF CACHE
# =====================================================================

RP_ACTIONS_CONFIG = {
    # Романтика & Забота
    "hug": {
        "aliases": ["обнять", "обнимашки", "обнял", "обняла"],
        "category": "hug",
        "verb": "крепко и с любовью обнял(а)",
        "emoji": "🤗",
        "quote": "Тепло и уют разливаются по сердцу... 🤍"
    },
    "kiss": {
        "aliases": ["поцеловать", "чмок", "поцелуй", "чмокнуть"],
        "category": "kiss",
        "verb": "нежно поцеловал(а)",
        "emoji": "💋",
        "quote": "Сладость этого момента не передать словами... ✨"
    },
    "pat": {
        "aliases": ["погладить", "погладил", "погладила", "гладить"],
        "category": "pat",
        "verb": "ласково погладил(а) по голове",
        "emoji": "🐾",
        "quote": "Хороший человек заслуживает немного ласки 🌸"
    },
    "cuddle": {
        "aliases": ["прижаться", "прильнуть", "обнять_уютно"],
        "category": "cuddle",
        "verb": "тепло и трепетно прижался(-ась) к",
        "emoji": "🧸",
        "quote": "Рядом так спокойно и безопасно... 🤍"
    },
    "tea": {
        "aliases": ["чай", "кофе", "напоить_чаем", "угостить_чаем"],
        "category": "sip",
        "verb": "заботливо налил(а) кружечку вкусного горячего чая для",
        "emoji": "☕️",
        "quote": "Уютная кружка согревает в любую непогоду 🫖"
    },
    "cure": {
        "aliases": ["вылечить", "полечить", "укутать"],
        "category": "lappillow",
        "verb": "укутал(а) тёплым пледом и вылечил(а)",
        "emoji": "💊",
        "quote": "Всё обязательно наладится, поправляйся скорее! 🩺"
    },
    "feed": {
        "aliases": ["покормить", "покормил", "угостить", "кормить"],
        "category": "feed",
        "verb": "заботливо покормил(а) вкусняшками",
        "emoji": "🍱",
        "quote": "Сытый человек — счастливый человек! 🍰"
    },
    "hand": {
        "aliases": ["взятьзаруку", "рука", "держатьзаруку"],
        "category": "handhold",
        "verb": "нежно взял(а) за руку",
        "emoji": "🤝",
        "quote": "Твоя ладонь в моей руке... 💫"
    },
    
    # Флирт
    "wink": {
        "aliases": ["подмигнуть", "подмигнул", "мигнуть"],
        "category": "wink",
        "verb": "заигрывающе подмигнул(а)",
        "emoji": "😉",
        "quote": "Между нами проскочила искра... ✨"
    },
    "bite": {
        "aliases": ["кусь", "укусить", "кусить"],
        "category": "bite",
        "verb": "игриво сделал(а) кусь за ушко",
        "emoji": "🦷",
        "quote": "Хрусь-кусь, теперь ты в моей власти! 🐾"
    },
    "blush": {
        "aliases": ["смущаться", "покраснел", "смутился", "покраснела"],
        "category": "blush",
        "verb": "густо покраснел(а) и засмущался(-ась) перед",
        "emoji": "😳",
        "quote": "Щёчки горят ярче летнего заката... 🌸"
    },
    
    # Агрессия & Битва
    "slap": {
        "aliases": ["пощечина", "пощёчина", "лещ", "датьлеща"],
        "category": "slap",
        "verb": "с размаху влепил(а) звучную пощёчину",
        "emoji": "👋",
        "quote": "Звонкий лещ возвращает в реальность! 💥"
    },
    "hit": {
        "aliases": ["ударить", "вмазать", "удар"],
        "category": "punch",
        "verb": "зарядил(а) мощный джеб прямо по",
        "emoji": "👊",
        "quote": "Критический урон зафиксирован! ⚡️"
    },
    "kick": {
        "aliases": ["пнуть", "пинок", "датьпинка"],
        "category": "kick",
        "verb": "смачно отвесил(а) мощный пинок",
        "emoji": "🦵",
        "quote": "Полетел красиво и с ускорением! 💨"
    },
    "shoot": {
        "aliases": ["выстрелить", "расстрелять", "пальнуть", "выстрел"],
        "category": "shoot",
        "verb": "без предупреждения открыл(а) огонь по",
        "emoji": "🔫",
        "quote": "Хэдшот без шансов на укрытие! 💥"
    },
    "kill": {
        "aliases": ["убить", "ликвидировать", "устранить"],
        "category": "yeet",
        "verb": "хладнокровно ликвидировал(а)",
        "emoji": "⚰️",
        "quote": "Wasted. Возрождение через 3... 2... 1... 💀"
    },
    
    # 18+ & Треш & Угар
    "spank": {
        "aliases": ["отшлепать", "отшлёпать", "шлепнуть", "шлёпнуть"],
        "category": "slap",
        "verb": "как следует отшлёпал(а) по попке",
        "emoji": "🍑",
        "quote": "Плохие мальчики и девочки должны быть наказаны! 🔥"
    },
    "burn": {
        "aliases": ["сжечь", "поджечь", "испепелить"],
        "category": "angry",
        "verb": "облил(а) бензином и дотла сжёг(-ла)",
        "emoji": "🔥",
        "quote": "Огонь очищает всё вокруг... Вызывайте пожарных! 🚒"
    },
    "jail": {
        "aliases": ["посадить", "арестовать", "в_тюрьму"],
        "category": "tableflip",
        "verb": "защёлкнул(а) наручники и упёк(-ла) в камеру",
        "emoji": "👮‍♂️",
        "quote": "Статья за шалости и превышение крутости! ⛓"
    },
    "choke": {
        "aliases": ["придушить", "задушить", "удавить"],
        "category": "angry",
        "verb": "в приступе ярости придушил(а)",
        "emoji": "🧤",
        "quote": "Дышите глубже, если сможете... 😵"
    },
    "bonk": {
        "aliases": ["бонк", "битой", "по_башке"],
        "category": "bonk",
        "verb": "смачно дал(а) по башке дубинкой",
        "emoji": "🔨",
        "quote": "Go to horny jail! BONK! 💫"
    },
    "dance": {
        "aliases": ["танцевать", "танец", "станцевать"],
        "category": "dance",
        "verb": "закружил(а) в безумном танце вместе с",
        "emoji": "💃",
        "quote": "Музыка гремит, танцуем до упаду! 🎶"
    },
    "drink": {
        "aliases": ["бухнуть", "выпить", "накатить", "тост"],
        "category": "sip",
        "verb": "залпом опрокинул(а) бокальчик за здоровье",
        "emoji": "🍻",
        "quote": "За нас, за вас и за красивый код! 🥂"
    },
    "smoke": {
        "aliases": ["покурить", "закурить", "подымить"],
        "category": "shrug",
        "verb": "задумчиво закурил(а) сигаретку рядом с",
        "emoji": "🚬",
        "quote": "Дым клубится, мысли улетают вдаль... 💨"
    },
    "cry": {
        "aliases": ["плакать", "поплакать", "рыдать"],
        "category": "cry",
        "verb": "горько расплакался(-ась) на плече у",
        "emoji": "😭",
        "quote": "Слёзы текут рекой, но станет легче... 💧"
    }
}

# In-memory cache for fast GIF URL fetching {category: [list_of_urls]}
_GIF_CACHE = {}

def get_rp_gif_url(category: str) -> str:
    """Fetches high-quality Anime GIF from nekos.best or fallback CDN."""
    cached = _GIF_CACHE.get(category)
    if cached and len(cached) > 0:
        return random.choice(cached)
    
    try:
        url = f"https://nekos.best/api/v2/{category}?amount=6"
        res = requests.get(url, timeout=3.5)
        if res.status_code == 200:
            data = res.json()
            results = data.get("results", [])
            urls = [r["url"] for r in results if "url" in r]
            if urls:
                _GIF_CACHE[category] = urls
                return random.choice(urls)
    except Exception as e:
        logger.debug(f"Nekos.best fetch error for {category}: {e}")
        
    # Safe static fallback GIF URLs
    fallbacks = [
        "https://media.giphy.com/media/u8M000N7B7l4c/giphy.gif",
        "https://media.giphy.com/media/l2QDM9Jnim1YV5ujC/giphy.gif",
        "https://media.giphy.com/media/3o7TKoWXm3okO1kgHC/giphy.gif"
    ]
    return random.choice(fallbacks)


# =====================================================================
# 2. TEXT ANIMATION ENGINE (TextFX)
# =====================================================================

def generate_animation_frames(anim_name: str, text: str) -> list:
    """Generates a sequence of text keyframes for in-place Telegram message editing."""
    clean_txt = (text or "").strip()
    if not clean_txt and anim_name != "moon":
        clean_txt = "AI FOR COPIL"
        
    frames = []
    
    if anim_name in ["type", "_type"]:
        step = max(1, len(clean_txt) // 7)
        for i in range(1, len(clean_txt) + 1, step):
            frames.append(clean_txt[:i] + "▌")
        if not frames or frames[-1] != clean_txt:
            frames.append(clean_txt)
            
    elif anim_name == "scrlt":
        # Marquee / scrolling banner
        w = min(14, max(8, len(clean_txt)))
        pad = " " * w
        s = pad + clean_txt + pad
        step = max(1, (len(clean_txt) + w) // 6)
        for i in range(0, len(clean_txt) + w + 1, step):
            chunk = s[i:i+w]
            frames.append(f"<code>[{chunk}]</code>")
        frames.append(clean_txt)
        
    elif anim_name == "shutter":
        # Blinds reveal effect
        n = len(clean_txt)
        shutter_1 = "".join("▌" if i % 2 == 0 else "░" for i in range(n))
        shutter_2 = "".join("█" if i % 2 == 0 else "▌" for i in range(n))
        shutter_3 = "".join(clean_txt[i] if i % 2 == 0 else "█" for i in range(n))
        frames = [
            f"<code>{shutter_1}</code>",
            f"<code>{shutter_2}</code>",
            f"<code>{shutter_3}</code>",
            clean_txt
        ]
        
    elif anim_name == "center":
        # Expansion from center outwards
        n = len(clean_txt)
        mid = n // 2
        steps = 5
        for s in range(1, steps):
            radius = int((s / steps) * (n / 2 + 1))
            start = max(0, mid - radius)
            end = min(n, mid + radius)
            pad_l = " " * start
            pad_r = " " * (n - end)
            frames.append(f"<code>{pad_l}{clean_txt[start:end]}{pad_r}</code>")
        frames.append(clean_txt)
        
    elif anim_name == "corners":
        # Meeting from both ends to center
        n = len(clean_txt)
        steps = 5
        for s in range(1, steps):
            w = max(1, int((s / steps) * (n / 2)))
            left = clean_txt[:w]
            right = clean_txt[n-w:]
            pad = " " * max(0, n - 2 * w)
            frames.append(f"<code>{left}{pad}{right}</code>")
        frames.append(clean_txt)
        
    elif anim_name == "blur":
        # Defocus to focus sharpness
        noise1 = "".join(random.choice(["░", "▒"]) if c != " " else " " for c in clean_txt)
        noise2 = "".join(random.choice(["▒", "▓"]) if c != " " else " " for c in clean_txt)
        partial = "".join(c if (i % 2 == 0 or c == " ") else "░" for i, c in enumerate(clean_txt))
        frames = [
            f"<code>{noise1}</code>",
            f"<code>{noise2}</code>",
            f"<code>{partial}</code>",
            clean_txt
        ]
        
    elif anim_name == "drop":
        # Vertical drop
        frames = [
            "<code>    ↓     </code>",
            "<code>  ↓ ↓ ↓   </code>",
            f"<code>{clean_txt[:max(1, len(clean_txt)//2)]}...</code>",
            clean_txt
        ]
        
    elif anim_name == "radar_scan":
        # Radar scan line
        n = min(12, len(clean_txt))
        frames = [
            "<code>[/        ]</code>",
            "<code>[- -      ]</code>",
            r"<code>[\ \ \    ]</code>",
            "<code>[| | | |  ]</code>",
            clean_txt
        ]
        
    elif anim_name == "rain":
        # Digital matrix rain
        matrix_glyphs = "01ｱｲｳｴ1001"
        for s in range(3):
            cur = "".join(c if random.random() < (s * 0.35) or c == " " else random.choice(matrix_glyphs) for c in clean_txt)
            frames.append(f"<code>{cur}</code>")
        frames.append(clean_txt)
        
    elif anim_name == "moon":
        # Moon phases
        frames = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘", "🌑", "🌕 ✨ <b>Full Moon</b>"]
        
    else:
        frames = [clean_txt]
        
    return frames

def run_text_animation(bot, chat_id, message_id, business_conn_id, anim_name: str, text: str):
    """Executes smooth in-place keyframe text animation in a non-blocking background thread."""
    def _worker():
        frames = generate_animation_frames(anim_name, text)
        for i, frame in enumerate(frames):
            is_last = (i == len(frames) - 1)
            try:
                if business_conn_id:
                    bot.edit_message_text(
                        text=frame,
                        chat_id=chat_id,
                        message_id=message_id,
                        business_connection_id=business_conn_id,
                        parse_mode="HTML"
                    )
                else:
                    bot.edit_message_text(
                        text=frame,
                        chat_id=chat_id,
                        message_id=message_id,
                        parse_mode="HTML"
                    )
            except Exception as e:
                # If rate-limited or identical edit, continue
                pass
            if not is_last:
                time.sleep(0.42)
                
    threading.Thread(target=_worker, daemon=True).start()


# =====================================================================
# 3. MEME & DEMOTIVATOR GENERATOR (.memez)
# =====================================================================

def generate_demotivator_image(img_bytes: bytes, title: str, subtitle: str = "") -> bytes:
    """Builds an authentic Demotivator meme image with black frame, white contour & classic fonts."""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    
    target_w = 640
    ratio = target_w / float(img.width)
    target_h = int(img.height * ratio)
    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    border_side = int(target_w * 0.08)
    border_top = int(target_w * 0.08)
    border_bottom = int(target_w * 0.28)
    
    total_w = target_w + border_side * 2
    total_h = target_h + border_top + border_bottom
    
    demo = Image.new("RGB", (total_w, total_h), color=(0, 0, 0))
    demo.paste(img, (border_side, border_top))
    
    draw = ImageDraw.Draw(demo)
    
    # White double frame around the inner image
    frame_gap = 5
    draw.rectangle([
        border_side - frame_gap, border_top - frame_gap,
        border_side + target_w + frame_gap, border_top + target_h + frame_gap
    ], outline=(255, 255, 255), width=2)
    
    # Fonts: Times New Roman or Arial
    font_path = "C:/Windows/Fonts/times.ttf" if os.path.exists("C:/Windows/Fonts/times.ttf") else "C:/Windows/Fonts/arial.ttf"
    title_size = max(24, int(target_w * 0.07))
    sub_size = max(16, int(target_w * 0.038))
    
    try:
        font_title = ImageFont.truetype(font_path, title_size)
        font_sub = ImageFont.truetype(font_path, sub_size)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        
    title_text = str(title).strip().upper() if title else "ДЕМОТИВАТОР"
    sub_text = str(subtitle).strip()
    
    center_x = total_w // 2
    title_y = border_top + target_h + int(border_bottom * 0.32)
    
    draw.text((center_x, title_y), title_text, fill=(255, 255, 255), font=font_title, anchor="mm")
    
    if sub_text:
        sub_y = title_y + int(title_size * 1.15)
        draw.text((center_x, sub_y), sub_text, fill=(255, 255, 255), font=font_sub, anchor="mm")
        
    out = io.BytesIO()
    demo.save(out, format="JPEG", quality=95)
    return out.getvalue()


# =====================================================================
# 4. OLBANSKIY / ПАДОНКАФФСКИЙ TRANSLATOR (.dumb)
# =====================================================================

def to_olbansky(text: str) -> str:
    """Converts regular text into authentic early-2000s Runet Olbanskiy / Падонкаффский slang."""
    if not text:
        return "Аффтар жжот! Пешы исчо, кросавчег!11 пыщ-пыщ!"
        
    words_map = {
        "привет": "превед",
        "медведь": "медвед",
        "красавчик": "кросавчег",
        "красавец": "кросавчег",
        "автор": "аффтар",
        "жжет": "жжот",
        "жжёт": "жжот",
        "пиши": "пешы",
        "еще": "исчо",
        "ещё": "исчо",
        "зачет": "зачот",
        "зачёт": "зачот",
        "спасибо": "пасиба",
        "пожалуйста": "пажалуста",
        "хорошо": "харашо",
        "отлично": "атлична",
        "человек": "чилавек",
        "собака": "собако",
        "девушка": "девачко",
        "картинка": "картинко",
        "смешно": "ржунимагу",
        "конечно": "канешно",
        "потому что": "патамушта",
        "сейчас": "щас",
        "тебе": "тибе",
        "себе": "сибе",
        "меня": "миня",
        "тебя": "тибя",
        "почему": "пачиму",
        "зачем": "зачемчег",
        "убейся": "убейсо ап стену",
        "выпей": "выпей йаду"
    }
    
    res = text
    for k, v in words_map.items():
        res = re.sub(r'(?i)\b' + re.escape(k) + r'\b', v, res)
        
    res = re.sub(r'(?i)ться\b', 'цца', res)
    res = re.sub(r'(?i)тся\b', 'цца', res)
    res = re.sub(r'(?i)ого\b', 'ова', res)
    res = re.sub(r'(?i)его\b', 'ева', res)
    res = re.sub(r'(?i)\bя\b', 'йа', res)
    res = re.sub(r'(?i)жи', 'жы', res)
    res = re.sub(r'(?i)ши', 'шы', res)
    res = re.sub(r'(?i)в\b', 'фф', res)
    if "!" in res:
        res = re.sub(r'!+', '!!11 пыщ-пыщ!', res)
    else:
        res += "!!11 пыщ-пыщ!"
        
    return res


# =====================================================================
# 5. TEXT STYLER (.bold)
# =====================================================================

def format_styled_text(text: str) -> str:
    """Formats text in multiple styles."""
    if not text:
        return (
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "┃ ✏️ <b>МЕНЮ СТИЛИЗАЦИИ ТЕКСТА</b> ┃\n"
            "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫\n"
            "┃ Используйте: <code>.bold [текст]</code>\n"
            "┃ \n"
            "┃ • <b>Жирный:</b> <code>&lt;b&gt;текст&lt;/b&gt;</code>\n"
            "┃ • <i>Курсив:</i> <code>&lt;i&gt;текст&lt;/i&gt;</code>\n"
            "┃ • <code>Моноширинный:</code> <code>&lt;code&gt;текст&lt;/code&gt;</code>\n"
            "┃ • <s>Зачеркнутый:</s> <code>&lt;s&gt;текст&lt;/s&gt;</code>\n"
            "┃ • <u>Подчеркнутый:</u> <code>&lt;u&gt;текст&lt;/u&gt;</code>\n"
            "┃ • <tg-spoiler>Спойлер:</tg-spoiler> <code>&lt;tg-spoiler&gt;текст&lt;/tg-spoiler&gt;</code>\n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
        )
    clean_esc = html.escape(text)
    return (
        f"<b>{clean_esc}</b>\n\n"
        f"<i>{clean_esc}</i>\n"
        f"<code>{clean_esc}</code>\n"
        f"<s>{clean_esc}</s>\n"
        f"<tg-spoiler>{clean_esc}</tg-spoiler>"
    )


# =====================================================================
# 6. DIALOG LINK GENERATOR (.link)
# =====================================================================

def generate_dialog_link(target_handle: str, prefilled_text: str = "") -> str:
    """Generates direct click-to-chat Telegram link with pre-filled text."""
    clean_h = (target_handle or "").strip().lstrip("@")
    if not clean_h:
        clean_h = "k3rnel8633"
    enc_txt = urllib.parse.quote(prefilled_text or "")
    link = f"https://t.me/{clean_h}?text={enc_txt}" if enc_txt else f"https://t.me/{clean_h}"
    return (
        f"🔗 <b>Прямая ссылка для диалога:</b>\n"
        f"<code>{link}</code>\n\n"
        f"💬 <i>При клике у пользователя сразу подставится этот текст в строку ввода!</i>"
    )


# =====================================================================
# 7. HIGH-LEVEL COMMAND HANDLERS
# =====================================================================

def find_rp_action(cmd_name: str):
    """Finds RP action config by command or alias."""
    c_low = cmd_name.lower().strip().lstrip("./!")
    if c_low in RP_ACTIONS_CONFIG:
        return c_low, RP_ACTIONS_CONFIG[c_low]
    for act_key, cfg in RP_ACTIONS_CONFIG.items():
        if c_low in cfg.get("aliases", []):
            return act_key, cfg
    return None, None

def handle_rp_command(bot, message, cmd_name: str, is_business: bool = False, business_conn_id: str = None):
    """Dispatches Roleplay action with anime GIF and structured card."""
    chat_id = message.chat.id
    act_key, cfg = find_rp_action(cmd_name)
    if not cfg:
        return False

    sender_name = message.from_user.first_name if message.from_user else "Пользователь"
    reply = getattr(message, 'reply_to_message', None)

    # Parse target
    raw_text = (message.text or getattr(message, 'caption', '') or '').strip()
    parts = raw_text.split(maxsplit=1)
    args = parts[1].strip() if len(parts) > 1 else ""

    if reply and reply.from_user:
        target_name = reply.from_user.first_name or "собеседника"
    elif args:
        target_name = args
    elif is_business and getattr(message, 'chat', None):
        target_name = message.chat.first_name or getattr(message.chat, 'title', '') or "собеседника"
    else:
        target_name = "всех вокруг"

    text = (
        f"{cfg['emoji']} <b>{html.escape(sender_name)}</b> {cfg['verb']} <b>{html.escape(target_name)}</b>!\n\n"
        f"<i>«{cfg['quote']}»</i>"
    )

    gif_url = get_rp_gif_url(cfg["category"])
    try:
        if is_business and business_conn_id:
            bot.send_animation(
                chat_id=chat_id,
                animation=gif_url,
                caption=text,
                parse_mode="HTML",
                business_connection_id=business_conn_id
            )
        else:
            bot.send_animation(
                chat_id=chat_id,
                animation=gif_url,
                caption=text,
                parse_mode="HTML",
                reply_to_message_id=reply.message_id if reply else None
            )
        return True
    except Exception as e:
        logger.debug(f"Could not send RP animation: {e}, falling back to text")
        try:
            if is_business and business_conn_id:
                bot.send_message(chat_id, text, parse_mode="HTML", business_connection_id=business_conn_id)
            else:
                bot.send_message(chat_id, text, parse_mode="HTML", reply_to_message_id=reply.message_id if reply else None)
            return True
        except Exception:
            return False

def handle_memez_command(bot, message, is_business: bool = False, business_conn_id: str = None):
    """Processes .memez [Top Text | Bottom Text] on replied photo."""
    chat_id = message.chat.id
    reply = getattr(message, 'reply_to_message', None)
    
    photo = None
    if reply and getattr(reply, 'photo', None):
        photo = reply.photo[-1]
    elif getattr(message, 'photo', None):
        photo = message.photo[-1]

    if not photo:
        notice = "⚠️ <b>Использование:</b> Ответьте на любое фото командой <code>.memez Верхний текст | Нижний текст</code>"
        if is_business and business_conn_id:
            try:
                bot.send_message(chat_id, notice, parse_mode="HTML", business_connection_id=business_conn_id)
            except Exception:
                pass
        else:
            bot.reply_to(message, notice, parse_mode="HTML")
        return

    raw_text = (message.text or getattr(message, 'caption', '') or '').strip()
    parts = raw_text.split(maxsplit=1)
    args = parts[1].strip() if len(parts) > 1 else ""

    if "|" in args:
        t_split = args.split("|", 1)
        title = t_split[0].strip()
        subtitle = t_split[1].strip()
    else:
        title = args or "ДЕМОТИВАТОР"
        subtitle = ""

    try:
        file_info = bot.get_file(photo.file_id)
        img_bytes = bot.download_file(file_info.file_path)
        demo_bytes = generate_demotivator_image(img_bytes, title, subtitle)

        if is_business and business_conn_id:
            bot.send_photo(chat_id=chat_id, photo=demo_bytes, business_connection_id=business_conn_id)
        else:
            bot.send_photo(chat_id=chat_id, photo=demo_bytes, reply_to_message_id=reply.message_id if reply else message.message_id)
    except Exception as e:
        logger.error(f"Error generating demotivator: {e}", exc_info=True)
        err_msg = f"⚠️ Ошибка создания демотиватора: {e}"
        if is_business and business_conn_id:
            try:
                bot.send_message(chat_id, err_msg, business_connection_id=business_conn_id)
            except Exception:
                pass
        else:
            bot.reply_to(message, err_msg)

def handle_spagif_command(bot, message, is_business: bool = False, business_conn_id: str = None):
    """Spams replied animation/sticker/photo N times (.spagif [count])."""
    chat_id = message.chat.id
    reply = getattr(message, 'reply_to_message', None)
    if not reply:
        notice = "⚠️ <b>Использование:</b> Ответьте на GIF/стикер/фото командой <code>.spagif [кол-во]</code>"
        if is_business and business_conn_id:
            try:
                bot.send_message(chat_id, notice, parse_mode="HTML", business_connection_id=business_conn_id)
            except Exception:
                pass
        else:
            bot.reply_to(message, notice, parse_mode="HTML")
        return

    raw_text = (message.text or getattr(message, 'caption', '') or '').strip()
    parts = raw_text.split()
    count = 5
    if len(parts) > 1 and parts[1].isdigit():
        count = min(max(1, int(parts[1])), 15)

    def _spam_worker():
        for _ in range(count):
            try:
                if reply.animation:
                    if is_business and business_conn_id:
                        bot.send_animation(chat_id, reply.animation.file_id, business_connection_id=business_conn_id)
                    else:
                        bot.send_animation(chat_id, reply.animation.file_id)
                elif reply.sticker:
                    if is_business and business_conn_id:
                        bot.send_sticker(chat_id, reply.sticker.file_id, business_connection_id=business_conn_id)
                    else:
                        bot.send_sticker(chat_id, reply.sticker.file_id)
                elif reply.photo:
                    if is_business and business_conn_id:
                        bot.send_photo(chat_id, reply.photo[-1].file_id, business_connection_id=business_conn_id)
                    else:
                        bot.send_photo(chat_id, reply.photo[-1].file_id)
                elif reply.document:
                    if is_business and business_conn_id:
                        bot.send_document(chat_id, reply.document.file_id, business_connection_id=business_conn_id)
                    else:
                        bot.send_document(chat_id, reply.document.file_id)
                time.sleep(0.38)
            except Exception as e:
                logger.debug(f"Spagif send error: {e}")
                break

    threading.Thread(target=_spam_worker, daemon=True).start()

def handle_automedia_command(bot, message, media_type: str, is_business: bool = False, business_conn_id: str = None, database = None):
    """Configures automatic media response (.autovideo, .autofile, .autophoto, .autoround, .autosticker)."""
    chat_id = message.chat.id
    owner_id = message.from_user.id if message.from_user else chat_id
    if is_business and business_conn_id and database:
        b_info = database.get_business_connection(business_conn_id)
        if b_info and b_info.get("user_id"):
            owner_id = int(b_info["user_id"])

    raw_text = (message.text or getattr(message, 'caption', '') or '').strip()
    parts = raw_text.split()
    arg = parts[1].lower() if len(parts) > 1 else ""

    key = f"automedia_{owner_id}_{media_type}"
    labels = {
        "video": "авто-видео",
        "file": "авто-файл",
        "photo": "авто-фото",
        "round": "авто-кружочек",
        "sticker": "авто-стикер"
    }
    lbl = labels.get(media_type, f"авто-{media_type}")

    if arg in ["off", "stop", "выкл", "откл", "0", "сброс"]:
        if database:
            database.set_app_setting(key, "")
        resp = f"🛑 <b>Режим «{lbl.capitalize()}» ВЫКЛЮЧЕН!</b>"
        if is_business and business_conn_id:
            try:
                bot.send_message(owner_id, resp, parse_mode="HTML")
            except Exception:
                pass
        else:
            bot.reply_to(message, resp, parse_mode="HTML")
        return

    reply = getattr(message, 'reply_to_message', None)
    file_id = None
    if reply:
        if media_type == "video" and getattr(reply, 'video', None):
            file_id = reply.video.file_id
        elif media_type == "file" and getattr(reply, 'document', None):
            file_id = reply.document.file_id
        elif media_type == "photo" and getattr(reply, 'photo', None):
            file_id = reply.photo[-1].file_id
        elif media_type == "round" and getattr(reply, 'video_note', None):
            file_id = reply.video_note.file_id
        elif media_type == "sticker" and getattr(reply, 'sticker', None):
            file_id = reply.sticker.file_id

    if not file_id:
        resp = (
            f"ℹ️ <b>Настройка «{lbl.capitalize()}»:</b>\n\n"
            f"Ответьте командой <code>.{message.text.split()[0].lstrip('./!')}</code> на нужное медиа ({lbl}), "
            f"чтобы сохранить его для автоответа.\n"
            f"Для отключения: <code>.{message.text.split()[0].lstrip('./!')} off</code>"
        )
        if is_business and business_conn_id:
            try:
                bot.send_message(owner_id, resp, parse_mode="HTML")
            except Exception:
                pass
        else:
            bot.reply_to(message, resp, parse_mode="HTML")
        return

    if database:
        database.set_app_setting(key, file_id)

    resp = (
        f"✅ <b>{lbl.capitalize()} успешно сохранено!</b>\n\n"
        f"Бот будет автоматически отправлять это медиа в ответ на сообщения собеседников в бизнес-чатах.\n"
        f"Для отключения отправьте: <code>.{message.text.split()[0].lstrip('./!')} off</code>"
    )
    if is_business and business_conn_id:
        try:
            bot.send_message(owner_id, resp, parse_mode="HTML")
        except Exception:
            pass
    else:
        bot.reply_to(message, resp, parse_mode="HTML")

def check_and_send_automedia(bot, chat_id: int, owner_id: int, business_conn_id: str, database) -> bool:
    """Checks if owner has any active automedia trigger and sends it."""
    if not database or not owner_id:
        return False
        
    for mtype in ["round", "video", "photo", "sticker", "file"]:
        key = f"automedia_{owner_id}_{mtype}"
        val = database.get_app_setting(key)
        if val and str(val).strip():
            fid = str(val).strip()
            try:
                if mtype == "video":
                    bot.send_video(chat_id, fid, business_connection_id=business_conn_id)
                elif mtype == "round":
                    bot.send_video_note(chat_id, fid, business_connection_id=business_conn_id)
                elif mtype == "photo":
                    bot.send_photo(chat_id, fid, business_connection_id=business_conn_id)
                elif mtype == "sticker":
                    bot.send_sticker(chat_id, fid, business_connection_id=business_conn_id)
                elif mtype == "file":
                    bot.send_document(chat_id, fid, business_connection_id=business_conn_id)
                return True
            except Exception as e:
                logger.debug(f"Auto-media {mtype} send error: {e}")
                return False
    return False

