import re

# Read ladder phrases and punches from bot code
with open(r'c:\Users\user\Desktop\pomoshotru_bot\bot.py', 'r', encoding='utf-8') as f:
    bot_code = f.read()

with open(r'c:\Users\user\Desktop\pomoshotru_bot\troll_arsenal.py', 'r', encoding='utf-8') as f:
    troll_code = f.read()

with open(r'c:\Users\user\Desktop\pomoshotru_bot\ai_roaster.py', 'r', encoding='utf-8') as f:
    ai_code = f.read()

# Extract GEMINI key
key_m = re.search(r'GEMINI_API_KEY\s*=\s*["\']([^"\']+)["\']', bot_code)
if not key_m:
    key_m = re.search(r'GEMINI_API_KEY\s*=\s*["\']([^"\']+)["\']', troll_code)
if not key_m:
    import sys
    sys.path.append(r'c:\Users\user\Desktop\pomoshotru_bot')
    import config
    gemini_key = getattr(config, 'GEMINI_API_KEY', '')
else:
    gemini_key = key_m.group(1)

print(f"Extracted Gemini API key: {gemini_key[:10]}...")

# Extract prompts and phrases
import sys
sys.path.append(r'c:\Users\user\Desktop\pomoshotru_bot')
from troll_arsenal import TROLL_LADDER_PHRASES, TROLL_PUNCHES, TROLL_TOXIC_TEMPLATES

print(f"Ladder: {len(TROLL_LADDER_PHRASES)}, Punches: {len(TROLL_PUNCHES)}, Toxic: {len(TROLL_TOXIC_TEMPLATES)}")
