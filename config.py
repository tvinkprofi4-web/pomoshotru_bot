import os
from dotenv import load_dotenv

load_dotenv()
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env_path):
    load_dotenv(_env_path, override=True)

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN", "")

# Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_IMAGE_API_KEY = os.getenv("GEMINI_IMAGE_API_KEY", "") or GEMINI_API_KEY

# Google Gemini Native Image Generation Models (Official Gemini Multimodal Image Output)
GEMINI_IMAGE_MODELS = [
    "gemini-2.5-flash-image",
    "gemini-3.1-flash-image",
    "gemini-3-pro-image",
    "gemini-3.1-flash-lite-image"
]


# Primary and Fallback Gemini Models (Prioritizing Active 2026 Models with High Quotas)
GEMINI_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash"
]

# Max history turns preserved per user
MAX_HISTORY_LEN = 16

# Creator & Developer Configuration
BOT_CREATOR_ID = 6363403785
BOT_CREATOR_USERNAME = "k3rnel8633"
BOT_CREATOR_NAME = "k3rnel"

COPIL_CREATOR_ID = 6363403785
COPIL_CREATOR_USERNAME = "k3rnel8633"
COPIL_CREATOR_NAME = "k3rnel"

DEV_MRZENUYT_ID = 7758799391
DEV_MRZENUYT_USERNAME = "ImNotRealQwQ"
DEV_MRZENUYT_NAME = "MrZenuyt"

# Verboo Code AI (Ultra Plan Quad Pool - Qwen 3.8 27B, DeepSeek V4 Pro, GLM 5.3 & MiniMax 3)
VERBOO_API_KEYS = [
    os.getenv("VERBOO_API_KEY_0", "vbk_ultra_84b379ce1a313051efdcb127b4d967feece38d0f"),
    os.getenv("VERBOO_API_KEY_1", "vbk_ultra_82dec488fa387763ac875f2aa146ab19d1715987"),
    os.getenv("VERBOO_API_KEY_2", "vbk_ultra_464b37fc95c96e42d170f2f6376163639dce8a79"),
    os.getenv("VERBOO_API_KEY_3", "vbk_ultra_c30913e5e077046805ffc748bcc5bbb407eccbff")
]
VERBOO_API_KEY = VERBOO_API_KEYS[0]
VERBOO_API_BASE = os.getenv("VERBOO_API_BASE", "https://code.verboo.ai/router/v1")
VERBOO_CODER_MODEL = os.getenv("VERBOO_CODER_MODEL", "deepseek-v4-pro")
VERBOO_FAST_MODEL = os.getenv("VERBOO_FAST_MODEL", "deepseek-v4.1-flash")
VERBOO_MODELS = [
    "qwen3.8-27b",
    "deepseek-v4-pro",
    "deepseek-v4-pro-0813",
    "deepseek-v4.1-flash",
    "glm-5.3",
    "glm-5.3-flash",
    "minimax-m3",
    "mimo-v2.6-flash"
]

# GitHub Integration & Credentials (Default configured for Creator k3rnel)
_CREATOR_DEFAULT_GH_TOKEN = "GIT_SECRET_TOKEN_REMOVED"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GIT_TOKEN") or os.getenv("GITHUB_PAT") or _CREATOR_DEFAULT_GH_TOKEN
GITHUB_REPO = os.getenv("GITHUB_REPO", "AUser7742/pomoshotru_bot")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
RENDER_BASE_URL = os.getenv("RENDER_BASE_URL", "https://pomoshotru-bot-i56y.onrender.com").rstrip("/")
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "kerneltop")
# Telegram Userbot / Premium MTProto Client Credentials (Official Telegram Client Keys)
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "6"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "eb06d4abfb49dc3eeb1aeb98ae0f581e")
_CREATOR_DEFAULT_SESSION_STRING = "1ApWapzMBu3vr2HgjR-jeYmTZPI0-CnpqYrMRZg_eetW4DVLUZlOir-mmTdEvy8Zi3GGwCJA57jRTBDN5kB_wLClOVte_9ViRzv2Gncel_D6JD0JV7sccFzjTbky51I3uQqfdPTHOh6mPUQPgJv6pv5sMva1rptDgK0Id_I9wxb0IfvYhsVY8nnmyhSseOBb59OO1RQOxHytUUq98LV3mg4UjeGqvgSG5b_gpwe4jnHbBLBZP_HEBrJUHsnhws7XXiqsCdhVbRJxcHMxl7kmwpNaGCkRqFK7WUMJwtckRhtR7DouQrrRVrMMeuldX9ke60VkDSyOrRAX1viy-TgNH1w4ZqUJ_xqc="
TELEGRAM_SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING") or _CREATOR_DEFAULT_SESSION_STRING

