import os
import sys
import json
import base64
import time
import urllib.request
import urllib.error

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
        print(f"[OK] Put {path}: {resp.status}")

# 1. Update TMessagesProj/src/main/res/values/extera.xml
print("=== 1. Updating values/extera.xml ===")
content, sha = get_file('TMessagesProj/src/main/res/values/extera.xml')
text = content.decode('utf-8', errors='ignore')
text = text.replace('<string name="exteraAppName" translatable="false">AyuGram</string>', '<string name="exteraAppName" translatable="false">Pomoshgram</string>')
text = text.replace('<string name="Preferences">exteraGram Preferences</string>', '<string name="Preferences">Pomoshgram Preferences</string>')
text = text.replace('exteraGram', 'Pomoshgram')
text = text.replace('AyuGram', 'Pomoshgram')
put_file('TMessagesProj/src/main/res/values/extera.xml', text.encode('utf-8'), 'feat(pomoshgram): rebrand extera.xml to Pomoshgram', sha)

# 2. Update TMessagesProj/src/main/res/values-ru/extera.xml
print("=== 2. Updating values-ru/extera.xml ===")
content, sha = get_file('TMessagesProj/src/main/res/values-ru/extera.xml')
text = content.decode('utf-8', errors='ignore')
text = text.replace('<string name="Preferences">Настройки exteraGram</string>', '<string name="Preferences">Настройки Pomoshgram</string>')
text = text.replace('exteraGram', 'Pomoshgram')
text = text.replace('AyuGram', 'Pomoshgram')
if 'exteraAppName' not in text:
    text = text.replace('<resources>', '<resources>\n    <string name="exteraAppName">Pomoshgram</string>')
put_file('TMessagesProj/src/main/res/values-ru/extera.xml', text.encode('utf-8'), 'feat(pomoshgram): rebrand values-ru/extera.xml to Pomoshgram', sha)

# 3. Update TMessagesProj/src/main/res/values/ayu.xml
print("=== 3. Updating values/ayu.xml ===")
content, sha = get_file('TMessagesProj/src/main/res/values/ayu.xml')
text = content.decode('utf-8', errors='ignore')
text = text.replace('<string name="AyuPreferences">AyuGram Preferences</string>', '<string name="AyuPreferences">Pomoshgram Preferences</string>')
text = text.replace('AyuGram', 'Pomoshgram')
text = text.replace('AyuSync', 'PomoshSync')
put_file('TMessagesProj/src/main/res/values/ayu.xml', text.encode('utf-8'), 'feat(pomoshgram): rebrand values/ayu.xml to Pomoshgram', sha)

# 4. Update TMessagesProj/src/main/res/values-ru/ayu.xml
print("=== 4. Updating values-ru/ayu.xml ===")
content, sha = get_file('TMessagesProj/src/main/res/values-ru/ayu.xml')
text = content.decode('utf-8', errors='ignore')
text = text.replace('<string name="AyuPreferences">Настройки AyuGram</string>', '<string name="AyuPreferences">Настройки Pomoshgram</string>')
text = text.replace('AyuGram', 'Pomoshgram')
text = text.replace('AyuSync', 'PomoshSync')
put_file('TMessagesProj/src/main/res/values-ru/ayu.xml', text.encode('utf-8'), 'feat(pomoshgram): rebrand values-ru/ayu.xml to Pomoshgram', sha)

# 5. Overwrite Adaptive Icon XMLs in mipmap-anydpi-v26
print("=== 5. Overwriting mipmap-anydpi-v26 Adaptive Icons ===")
adaptive_xml = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@mipmap/ic_launcher"/>
    <foreground android:drawable="@mipmap/ic_launcher"/>
</adaptive-icon>
""".encode('utf-8')

aliases = [
    'ic_launcher.xml', 'ic_launcher_monet.xml', 'ic_launcher_gradient.xml',
    'ic_launcher_google.xml', 'ic_launcher_480dsgn.xml', 'ic_launcher_aurora.xml',
    'ic_launcher_space.xml', 'ic_launcher_winter.xml', 'ic_launcher_neo.xml',
    'ic_launcher_orbit.xml', 'ic_launcher_amethyst.xml', 'ic_launcher_sus.xml',
    'ic_launcher_beta.xml'
]

for alias in aliases:
    put_file(f'TMessagesProj/src/main/res/mipmap-anydpi-v26/{alias}', adaptive_xml, f'feat(pomoshgram): set {alias} to 3D cyberpunk Pomoshgram icon')

# 6. Overwrite drawable/ic_foreground.xml with bitmap referencing ic_launcher
print("=== 6. Overwrite drawable/ic_foreground.xml ===")
bitmap_xml = """<?xml version="1.0" encoding="utf-8"?>
<bitmap xmlns:android="http://schemas.android.com/apk/res/android"
    android:src="@mipmap/ic_launcher"
    android:gravity="center" />
""".encode('utf-8')
put_file('TMessagesProj/src/main/res/drawable/ic_foreground.xml', bitmap_xml, 'feat(pomoshgram): replace ic_foreground with Pomoshgram bitmap')

# 7. Update TMessagesProj/src/main/AndroidManifest.xml DefaultIcon
print("=== 7. Updating AndroidManifest.xml DefaultIcon ===")
content, sha = get_file('TMessagesProj/src/main/AndroidManifest.xml')
text = content.decode('utf-8', errors='ignore')

target_alias = '<activity-alias\n            android:name="com.exteragram.messenger.DefaultIcon"'
replacement_alias = '<activity-alias\n            android:name="com.exteragram.messenger.DefaultIcon"\n            android:icon="@mipmap/ic_launcher"\n            android:roundIcon="@mipmap/ic_launcher_round"\n            android:label="@string/exteraAppName"'

if target_alias in text:
    text = text.replace(target_alias, replacement_alias)
    put_file('TMessagesProj/src/main/AndroidManifest.xml', text.encode('utf-8'), 'feat(pomoshgram): explicitly enforce ic_launcher on DefaultIcon alias', sha)
else:
    print("Warning: target_alias not found in AndroidManifest.xml")

# 8. Update AyuConstants.java with NullSecAI links
print("=== 8. Updating AyuConstants.java with NullSecAI links ===")
content, sha = get_file('TMessagesProj/src/main/java/com/radolyn/ayugram/AyuConstants.java')
text = content.decode('utf-8', errors='ignore')
text = text.replace('public static String APP_NAME = "AyuGram";', 'public static String APP_NAME = "Pomoshgram";')
text = text.replace('public static String APP_NAME = "ayuGram";', 'public static String APP_NAME = "Pomoshgram";')
text = text.replace('public static String APP_GITHUB = "AyuGram/AyuGram4A";', f'public static String APP_GITHUB = "{REPO}";')

# Replace channel/chat urls if defined
lines = []
for line in text.splitlines():
    if 'APP_CHANNEL' in line or 'APP_CHAT' in line:
        line = re.sub(r'\"https://t\.me/[^\"]+\"', '\"https://t.me/NullSecAI\"', line)
    lines.append(line)
text = '\n'.join(lines)
put_file('TMessagesProj/src/main/java/com/radolyn/ayugram/AyuConstants.java', text.encode('utf-8'), 'feat(pomoshgram): set official channel to NullSecAI in AyuConstants', sha)

# 9. Trigger automated build workflow
print("=== 9. Triggering automated build workflow ===")
disp_url = f"https://api.github.com/repos/{REPO}/actions/workflows/release.yml/dispatches"
disp_payload = json.dumps({'ref': BRANCH}).encode('utf-8')
disp_req = urllib.request.Request(disp_url, data=disp_payload, headers=HEADERS, method='POST')
with urllib.request.urlopen(disp_req) as resp:
    print(f"Triggered final rebranded build! Status: {resp.status}")

print("\nREBRAND DEPLOYMENT COMPLETED SUCCESSFULLY!")
