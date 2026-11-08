import re

path = r'c:\Users\user\Desktop\pomoshotru_bot\ai_roaster.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

replacement = '''ACTIVE_GEMINI_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.1-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest"
]'''

text = re.sub(r'ACTIVE_GEMINI_MODELS = \[[^\]]*\]', replacement, text)

with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(text)

print('Updated ai_roaster.py!')
