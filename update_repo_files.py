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

# 1. Update TMessagesProj/build.gradle to build arm64-v8a specifically
url_bg = f"https://api.github.com/repos/{REPO}/contents/TMessagesProj/build.gradle?ref={BRANCH}"
req_bg = urllib.request.Request(url_bg, headers=HEADERS)
with urllib.request.urlopen(req_bg) as resp:
    data_bg = json.loads(resp.read().decode())
    sha_bg = data_bg['sha']
    content_bg = base64.b64decode(data_bg['content']).decode('utf-8', errors='ignore')

old_str = 'ndk.abiFilters "armeabi-v7a", "arm64-v8a", "x86", "x86_64"'
new_str = 'ndk.abiFilters "arm64-v8a"'

if old_str in content_bg:
    content_bg = content_bg.replace(old_str, new_str)
    put_data = {
        'message': 'perf(pomoshgram): target 64-bit arm64-v8a for speed and efficiency',
        'content': base64.b64encode(content_bg.encode('utf-8')).decode('utf-8'),
        'sha': sha_bg,
        'branch': BRANCH
    }
    put_req = urllib.request.Request(url_bg, data=json.dumps(put_data).encode('utf-8'), headers=HEADERS, method='PUT')
    with urllib.request.urlopen(put_req) as resp:
        print("Updated TMessagesProj/build.gradle to arm64-v8a:", resp.status)
else:
    print("Old ABI string not found or already updated.")

# 2. Update .github/workflows/release.yml to generate the two missing Java classes on the fly!
url_wf = f"https://api.github.com/repos/{REPO}/contents/.github/workflows/release.yml?ref={BRANCH}"
req_wf = urllib.request.Request(url_wf, headers=HEADERS)
with urllib.request.urlopen(req_wf) as resp:
    data_wf = json.loads(resp.read().decode())
    sha_wf = data_wf['sha']

new_workflow = """name: Build Pomoshgram APK
on:
  push:
    branches:
      - rewrite
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Source Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Java 17
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
          cache: 'gradle'

      - name: Free Disk Space & Install Build Tools
        run: |
          sudo rm -rf /usr/share/dotnet/
          sudo rm -rf /usr/local/graalvm/
          sudo rm -rf /usr/local/.ghcup/
          sudo rm -rf /usr/local/share/powershell
          sudo rm -rf /usr/local/share/chromium
          sudo rm -rf /usr/local/lib/node_modules
          sudo apt-get update && sudo apt-get install -y bison gcc make curl ninja-build ccache

      - name: Setup Android NDK and CMake
        run: |
          yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --licenses || true
          $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager "ndk;21.4.7075529" "cmake;3.10.2.4988404"
          echo "ANDROID_NDK_HOME=$ANDROID_HOME/ndk/21.4.7075529" >> $GITHUB_ENV
          echo "ANDROID_NDK_ROOT=$ANDROID_HOME/ndk/21.4.7075529" >> $GITHUB_ENV

      - name: Prepare API_KEYS, Keystore & Proprietary Stubs
        run: |
          mkdir -p TMessagesProj/config
          rm -f TMessagesProj/config/extera.jks
          keytool -genkeypair -v -keystore TMessagesProj/config/extera.jks -alias pomosh -keyalg RSA -keysize 2048 -validity 10000 -storepass pomoshpassword -keypass pomoshpassword -dname "CN=Pomoshgram, OU=Dev, O=Pomoshgram, L=Tashkent, S=Tashkent, C=UZ"
          cat << 'EOF' > ./API_KEYS
          APP_ID = 6
          APP_HASH = "eb06d4abfb49dc3eeb1aeb98ae0f581e"
          MAPS_V2_API = ""
          
          SIGNING_KEY_PASSWORD = pomoshpassword
          SIGNING_KEY_ALIAS = pomosh
          SIGNING_KEY_STORE_PASSWORD = pomoshpassword
          EOF

          # Create proprietary classes
          rm -rf TMessagesProj/src/main/java/com/radolyn/ayugram/proprietary
          mkdir -p TMessagesProj/src/main/java/com/radolyn/ayugram/proprietary

          cat << 'EOF' > TMessagesProj/src/main/java/com/radolyn/ayugram/proprietary/AyuHistoryHook.java
          package com.radolyn.ayugram.proprietary;

          public class AyuHistoryHook {
          }
          EOF

          cat << 'EOF' > TMessagesProj/src/main/java/com/radolyn/ayugram/proprietary/AyuMessageUtils.java
          package com.radolyn.ayugram.proprietary;

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
              }
          }
          EOF

      - name: Set up ccache
        uses: hendrikmuhs/ccache-action@v1.2
        with:
          key: ccache
          restore-keys: ccache

      - name: Grant execute permission for gradlew
        run: chmod +x gradlew

      - name: Build Pomoshgram APK
        run: ./gradlew assembleAfatRelease --no-daemon --stacktrace

      - name: Upload Pomoshgram APK Artifact
        uses: actions/upload-artifact@v4
        with:
          name: Pomoshgram-Release-APK
          path: TMessagesProj/build/outputs/apk/**/*.apk
"""

put_wf_data = {
    'message': 'ci(pomoshgram): embed AyuMessageUtils and AyuHistoryHook stubs',
    'content': base64.b64encode(new_workflow.encode('utf-8')).decode('utf-8'),
    'sha': sha_wf,
    'branch': BRANCH
}
put_wf_req = urllib.request.Request(url_wf, data=json.dumps(put_wf_data).encode('utf-8'), headers=HEADERS, method='PUT')
with urllib.request.urlopen(put_wf_req) as resp:
    print("Updated .github/workflows/release.yml:", resp.status)

# 3. Trigger workflow dispatch
disp_url = f"https://api.github.com/repos/{REPO}/actions/workflows/release.yml/dispatches"
disp_payload = json.dumps({'ref': BRANCH}).encode('utf-8')
disp_req = urllib.request.Request(disp_url, data=disp_payload, headers=HEADERS, method='POST')
with urllib.request.urlopen(disp_req) as resp:
    print(f"Workflow dispatched: {resp.status}")
