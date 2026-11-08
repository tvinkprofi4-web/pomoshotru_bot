import urllib.request
import json
import base64

TOKEN = 'GIT_SECRET_TOKEN_REMOVED'
HEADERS = {
    'Authorization': f'token {TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'Pomosh'
}
REPO = 'AUser7742/Pomoshgram'
BRANCH = 'rewrite'

def put_file(path, content, message):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}"
    sha = None
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            sha = data['sha']
    except Exception:
        pass
    
    put_data = {
        'message': message,
        'content': base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        'branch': BRANCH
    }
    if sha:
        put_data['sha'] = sha
        
    put_req = urllib.request.Request(url, data=json.dumps(put_data).encode('utf-8'), headers=HEADERS, method='PUT')
    with urllib.request.urlopen(put_req) as resp:
        print(f"Uploaded {path}: {resp.status}")

# 1. AyuMessageUtils.java
ayu_message_utils = """package com.radolyn.ayugram.proprietary;

import com.radolyn.ayugram.database.entities.AyuMessageBase;
import com.radolyn.ayugram.messages.AyuSavePreferences;
import org.telegram.messenger.MessageObject;
import org.telegram.tgnet.TLRPC;

public class AyuMessageUtils {

    public static void map(AyuSavePreferences prefs, AyuMessageBase entity) {
        if (prefs == null || entity == null) return;
        TLRPC.Message msg = prefs.getMessage();
        entity.userId = prefs.getUserId();
        entity.dialogId = prefs.getDialogId();
        entity.topicId = prefs.getTopicId();
        entity.messageId = prefs.getMessageId();
        entity.entityCreateDate = prefs.getRequestCatchTime();

        if (msg != null) {
            entity.groupedId = msg.grouped_id;
            entity.fromId = MessageObject.getFromChatId(msg);
            entity.peerId = MessageObject.getPeerId(msg);
            entity.date = msg.date;
            entity.flags = msg.flags;
            entity.editDate = msg.edit_date;
            entity.views = msg.views;
            entity.text = msg.message;
        }
    }

    public static void mapMedia(AyuSavePreferences prefs, AyuMessageBase entity, boolean copyMedia) {
        // Safe stub for media caching
    }

    public static void map(AyuMessageBase entity, TLRPC.Message msg, int currentAccount) {
        if (entity == null || msg == null) return;
        msg.id = entity.messageId;
        msg.date = entity.date;
        msg.dialog_id = entity.dialogId;
        msg.message = entity.text;
        msg.flags = entity.flags;
        msg.edit_date = entity.editDate;
        msg.views = entity.views;
        msg.grouped_id = entity.groupedId;
    }

    public static void mapMedia(AyuMessageBase entity, TLRPC.Message msg) {
        // Safe stub for media preview
    }
}
"""

put_file('TMessagesProj/src/main/java/com/radolyn/ayugram/proprietary/AyuMessageUtils.java', ayu_message_utils, 'feat(pomoshgram): implement AyuMessageUtils mapper')

# 2. AyuHistoryHook.java
ayu_history_hook = """package com.radolyn.ayugram.proprietary;

public class AyuHistoryHook {
}
"""

put_file('TMessagesProj/src/main/java/com/radolyn/ayugram/proprietary/AyuHistoryHook.java', ayu_history_hook, 'feat(pomoshgram): add AyuHistoryHook stub')

# 3. Optimize TMessagesProj/build.gradle to build arm64-v8a specifically
bg_url = f"https://api.github.com/repos/{REPO}/contents/TMessagesProj/build.gradle?ref={BRANCH}"
bg_req = urllib.request.Request(bg_url, headers=HEADERS)
with urllib.request.urlopen(bg_req) as resp:
    bg_data = json.loads(resp.read().decode())
    bg_sha = bg_data['sha']
    bg_content = base64.b64decode(bg_data['content']).decode('utf-8', errors='ignore')

# Target arm64-v8a for afat
old_abi = 'ndk.abiFilters "armeabi-v7a", "arm64-v8a", "x86", "x86_64"'
new_abi = 'ndk.abiFilters "arm64-v8a"'
if old_abi in bg_content:
    bg_content = bg_content.replace(old_abi, new_abi)
    put_file('TMessagesProj/build.gradle', bg_content, 'perf(pomoshgram): target 64-bit ARM arm64-v8a for faster build')
    print("TMessagesProj/build.gradle updated to arm64-v8a")
else:
    print("Old abi string not found, check build.gradle")

# 4. Trigger workflow dispatch
disp_url = f"https://api.github.com/repos/{REPO}/actions/workflows/release.yml/dispatches"
disp_payload = json.dumps({'ref': BRANCH}).encode('utf-8')
disp_req = urllib.request.Request(disp_url, data=disp_payload, headers=HEADERS, method='POST')
with urllib.request.urlopen(disp_req) as resp:
    print(f"Triggered new release build: {resp.status}")
