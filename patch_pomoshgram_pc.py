import os
import shutil

exe_path = r'c:\Users\user\Desktop\Pomoshgram_PC\Pomoshgram.exe'
new_path = r'c:\Users\user\Desktop\Pomoshgram_PC\Pomoshgram_new.exe'

with open(exe_path, 'rb') as f:
    data = bytearray(f.read())

count = 0

def replace_utf16(data, old_str, new_str):
    global count
    old_b = old_str.encode('utf-16le')
    if len(new_str) < len(old_str):
        new_str = new_str.ljust(len(old_str), ' ')
    elif len(new_str) > len(old_str):
        new_str = new_str[:len(old_str)]
    new_b = new_str.encode('utf-16le')
    
    pos = 0
    while True:
        p = data.find(old_b, pos)
        if p == -1:
            break
        data[p:p+len(old_b)] = new_b
        count += 1
        pos = p + len(old_b)

def replace_ascii(data, old_str, new_str):
    global count
    old_b = old_str.encode('ascii')
    if len(new_str) < len(old_str):
        new_str = new_str.ljust(len(old_str), ' ')
    elif len(new_str) > len(old_str):
        new_str = new_str[:len(old_str)]
    new_b = new_str.encode('ascii')
    
    pos = 0
    while True:
        p = data.find(old_b, pos)
        if p == -1:
            break
        data[p:p+len(old_b)] = new_b
        count += 1
        pos = p + len(old_b)

# 1. UI Titles & Settings
replace_utf16(data, 'AyuGram Preferences', 'Pomoshgram Settings')
replace_utf16(data, 'AyuGram.AyuGramDesktop', 'Pomoshgram.Desktop    ')
replace_utf16(data, 'Export AyuGram Database?', 'Export Pomosh  Database?')
replace_utf16(data, 'Import AyuGram Database?', 'Import Pomosh  Database?')
replace_utf16(data, 'AyuGram Attachments Folder', 'Pomoshgram Storage Folder ')
replace_utf16(data, 'AyuGram Messages Database', 'Pomoshgram Messages DB   ')
replace_utf16(data, 'AyuGram Push Service', 'Pomoshgram Background')
replace_utf16(data, 'official AyuGram chat', 'official NullSec chat')
replace_utf16(data, 'AyuGram is **free** software', 'Pomoshgram is **free** client')
replace_utf16(data, 'related to AyuGram in exteraGram', 'related to Pomosh  in NullSec   ')
replace_utf16(data, 'AyuGram Desktop', 'Pomoshgram PC  ')

# 2. URLs -> NullSecAI
replace_ascii(data, 'https://t.me/ayugramchat', 'https://t.me/NullSecAI  ')
replace_ascii(data, 'https://t.me/ayugram', 'https://t.me/NullSecAI')
replace_ascii(data, 't.me/ayugram', 't.me/NullSecAI')
replace_ascii(data, 't.me/exteragram', 't.me/NullSecAI ')
replace_ascii(data, 'https://github.com/AyuGram', 'https://t.me/NullSecAI    ')

# 3. Visual Stars in Profile:
# In Settings menu, 'My Stars' -> '⭐ 999M Stars'
replace_utf16(data, 'My Stars', '⭐999999M')

print("Writing patched binary to Pomoshgram_new.exe...")
with open(new_path, 'wb') as f:
    f.write(data)

print(f"Applied {count} binary patches successfully!")
