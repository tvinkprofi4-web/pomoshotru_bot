import os
import sys
import json
import base64
import time
import io
import urllib.request
from PIL import Image

TOKEN = 'GIT_SECRET_TOKEN_REMOVED'
REPO = 'tvinkprofi4-web/Pomoshgram'
BRANCH = 'rewrite'
HEADERS = {
    'Authorization': f'token {TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'Pomosh'
}

def get_file(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        blob_sha = data['sha']
    
    url_blob = f"https://api.github.com/repos/{REPO}/git/blobs/{blob_sha}"
    req_blob = urllib.request.Request(url_blob, headers=HEADERS)
    with urllib.request.urlopen(req_blob) as resp:
        content = base64.b64decode(json.loads(resp.read().decode())['content'])
        return content, blob_sha

def put_file(path, content_bytes, message, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}"
    if sha is None:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                sha = data['sha']
        except Exception:
            sha = None
            
    payload = {
        'message': message,
        'content': base64.b64encode(content_bytes).decode('utf-8'),
        'branch': BRANCH
    }
    if sha:
        payload['sha'] = sha
        
    put_req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=HEADERS, method='PUT')
    with urllib.request.urlopen(put_req) as resp:
        print(f"Put {path}: {resp.status}")

def delete_file(path, message):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            sha = data['sha']
            
        payload = json.dumps({'message': message, 'sha': sha, 'branch': BRANCH}).encode('utf-8')
        del_req = urllib.request.Request(url, data=payload, headers=HEADERS, method='DELETE')
        with urllib.request.urlopen(del_req) as resp:
            print(f"Deleted {path}: {resp.status}")
    except Exception as e:
        print(f"Delete {path} skipped: {e}")

print("=== 1. Delete .gitmodules ===")
delete_file('.gitmodules', 'ci(pomoshgram): remove broken proprietary submodule')

print("=== 2. Update Strings (AppName & exteraAppName) ===")
str_content, str_sha = get_file('TMessagesProj/src/main/res/values/strings.xml')
str_text = str_content.decode('utf-8', errors='ignore')
str_text = str_text.replace('<string name="exteraAppName">ayuGram</string>', '<string name="exteraAppName">Pomoshgram</string>')
str_text = str_text.replace('<string name="AppName">ayuGram</string>', '<string name="AppName">Pomoshgram</string>')
str_text = str_text.replace('<string name="AppName">Telegram</string>', '<string name="AppName">Pomoshgram</string>')
str_text = str_text.replace('<string name="ApplicationName">ayuGram</string>', '<string name="ApplicationName">Pomoshgram</string>')
put_file('TMessagesProj/src/main/res/values/strings.xml', str_text.encode('utf-8'), 'feat(pomoshgram): rename app to Pomoshgram', str_sha)

print("=== 3. Enable localPremium by default in AyuConfig.java ===")
cfg_content, cfg_sha = get_file('TMessagesProj/src/main/java/com/radolyn/ayugram/AyuConfig.java')
cfg_text = cfg_content.decode('utf-8', errors='ignore')
cfg_text = cfg_text.replace('public static boolean localPremium;', 'public static boolean localPremium = true;')
cfg_text = cfg_text.replace('public static boolean localPremium = false;', 'public static boolean localPremium = true;')
put_file('TMessagesProj/src/main/java/com/radolyn/ayugram/AyuConfig.java', cfg_text.encode('utf-8'), 'feat(pomoshgram): enable local premium by default for custom folder emojis', cfg_sha)

print("=== 4. Update AyuConstants.java ===")
cst_content, cst_sha = get_file('TMessagesProj/src/main/java/com/radolyn/ayugram/AyuConstants.java')
cst_text = cst_content.decode('utf-8', errors='ignore')
cst_text = cst_text.replace('APP_NAME = "ayuGram"', 'APP_NAME = "Pomoshgram"')
cst_text = cst_text.replace('APP_GITHUB = "AyuGram/AyuGram4A"', f'APP_GITHUB = "{REPO}"')
put_file('TMessagesProj/src/main/java/com/radolyn/ayugram/AyuConstants.java', cst_text.encode('utf-8'), 'feat(pomoshgram): update constants', cst_sha)

print("=== 5. Hook SendMessagesHelper.java ===")
smh_content, smh_sha = get_file('TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java')
smh_text = smh_content.decode('utf-8', errors='ignore')
target_hook = "public void sendMessage(Object messageObject, MessageObject replyToMsg, MessageObject replyToStoryMsg, TLRPC.TL_forumTopic forumTopic, long peer, boolean notify, boolean schedule, boolean forward, int ttl, long effectId, int flags) {"
replacement_hook = """public void sendMessage(Object messageObject, MessageObject replyToMsg, MessageObject replyToStoryMsg, TLRPC.TL_forumTopic forumTopic, long peer, boolean notify, boolean schedule, boolean forward, int ttl, long effectId, int flags) {
        if (com.pomoshgram.PomoshEngine.handleOutgoingMessage(currentAccount, messageObject, peer, replyToMsg)) {
            return;
        }"""
if target_hook in smh_text:
    smh_text = smh_text.replace(target_hook, replacement_hook)
    put_file('TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java', smh_text.encode('utf-8'), 'feat(pomoshgram): hook sendMessage for stealth command suppression', smh_sha)
else:
    print("Warning: target hook signature not found in SendMessagesHelper.java!")

print("=== 6. Deploy Custom 3D App Icon ===")
icon_path = r'C:\Users\user\Desktop\Pomoshgram_Icon.jpg'
base_img = Image.open(icon_path).convert('RGBA')

sizes = {
    'mipmap-mdpi': 48,
    'mipmap-hdpi': 72,
    'mipmap-xhdpi': 96,
    'mipmap-xxhdpi': 144,
    'mipmap-xxxhdpi': 192
}

for folder, sz in sizes.items():
    resized = base_img.resize((sz, sz), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    resized.save(buf, format='PNG')
    png_bytes = buf.getvalue()
    
    # Save ic_launcher.png
    put_file(f'TMessagesProj/src/main/res/{folder}/ic_launcher.png', png_bytes, f'feat(pomoshgram): update {folder} ic_launcher.png')
    put_file(f'TMessagesProj/src/main/res/{folder}/ic_launcher_round.png', png_bytes, f'feat(pomoshgram): update {folder} ic_launcher_round.png')

print("=== 7. Target 64-bit arm64-v8a in build.gradle ===")
bg_content, bg_sha = get_file('TMessagesProj/build.gradle')
bg_text = bg_content.decode('utf-8', errors='ignore')
old_abi = 'ndk.abiFilters "armeabi-v7a", "arm64-v8a", "x86", "x86_64"'
new_abi = 'ndk.abiFilters "arm64-v8a"'
if old_abi in bg_text:
    bg_text = bg_text.replace(old_abi, new_abi)
    put_file('TMessagesProj/build.gradle', bg_text.encode('utf-8'), 'perf(pomoshgram): target pure 64-bit arm64-v8a', bg_sha)

print("Setup completed step 1-7.")
