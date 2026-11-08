import os
import sys
import json
import base64
import time
import io
import re
import urllib.request
import urllib.error
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
        print(f"[OK] Put {path}: {resp.status}")

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
            print(f"[OK] Deleted {path}: {resp.status}")
    except Exception as e:
        print(f"[SKIP] Delete {path}: {e}")

print("=== 1. Delete .gitmodules ===")
delete_file('.gitmodules', 'ci(pomoshgram): remove broken proprietary submodule')

print("=== 2. Update Strings (AppName & exteraAppName) ===")
str_content, str_sha = get_file('TMessagesProj/src/main/res/values/strings.xml')
str_text = str_content.decode('utf-8', errors='ignore')
str_text = str_text.replace('<string name="exteraAppName">ayuGram</string>', '<string name="exteraAppName">Pomoshgram</string>')
str_text = str_text.replace('<string name="AppName">ayuGram</string>', '<string name="AppName">Pomoshgram</string>')
str_text = str_text.replace('<string name="AppName">Telegram</string>', '<string name="AppName">Pomoshgram</string>')
str_text = str_text.replace('<string name="ApplicationName">ayuGram</string>', '<string name="ApplicationName">Pomoshgram</string>')
str_text = str_text.replace('<string name="AppNameBeta">Telegram Beta</string>', '<string name="AppNameBeta">Pomoshgram</string>')
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
cst_text = cst_text.replace('APP_NAME = "AyuGram"', 'APP_NAME = "Pomoshgram"')
cst_text = cst_text.replace('APP_GITHUB = "AyuGram/AyuGram4A"', f'APP_GITHUB = "{REPO}"')
put_file('TMessagesProj/src/main/java/com/radolyn/ayugram/AyuConstants.java', cst_text.encode('utf-8'), 'feat(pomoshgram): update constants', cst_sha)

print("=== 5. Hook SendMessagesHelper.java ===")
smh_content, smh_sha = get_file('TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java')
smh_text = smh_content.decode('utf-8', errors='ignore')
target_hook = "        // --- AyuGram hook\n\n        String originalPath = null;"
replacement_hook = """        // --- AyuGram hook

        // --- Pomoshgram Userbot Hook
        if (com.pomoshgram.PomoshEngine.handleOutgoingMessage(currentAccount, message, peer, replyToMsg)) {
            return;
        }

        String originalPath = null;"""

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

print("=== 8. Build & Upload PomoshEngine.java ===")
sys.path.append(r'c:\Users\user\Desktop\pomoshotru_bot')
from troll_arsenal import TROLL_LADDER_PHRASES, TROLL_PUNCHES

def escape_java(s):
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '')

ladder_items = ',\n        '.join(f'"{escape_java(p)}"' for p in TROLL_LADDER_PHRASES[:120])
punches_items = ',\n        '.join(f'"{escape_java(p)}"' for p in TROLL_PUNCHES[:120])

pomosh_engine_code = f'''package com.pomoshgram;

import android.text.TextUtils;
import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.MessageObject;
import org.telegram.messenger.MessagesController;
import org.telegram.messenger.SendMessagesHelper;
import org.telegram.tgnet.TLRPC;

import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;

public class PomoshEngine {{

    public static volatile boolean enabled = true;
    public static volatile int ladderSpeedMs = 280;
    public static final ConcurrentHashMap<Long, Boolean> activeCancels = new ConcurrentHashMap<>();
    public static final ConcurrentHashMap<Long, Long> chatTargets = new ConcurrentHashMap<>();
    public static final ConcurrentHashMap<Long, String> chatTargetNames = new ConcurrentHashMap<>();

    public static final String[] LADDER_PHRASES = new String[] {{
        {ladder_items}
    }};

    public static final String[] PUNCHES = new String[] {{
        {punches_items}
    }};

    public static boolean handleOutgoingMessage(int account, String message, long peer, MessageObject replyToMsg) {{
        if (!enabled || TextUtils.isEmpty(message)) {{
            return false;
        }}

        String trimmed = message.trim();
        if (!trimmed.startsWith(".") && !trimmed.startsWith("!")) {{
            return false;
        }}

        String[] parts = trimmed.split("\\\\s+");
        String rawCmd = parts[0].substring(1).toLowerCase();

        // 1. .ladder / .лесенка (Infinite Continuous until .stop)
        if (rawCmd.equals("ladder") || rawCmd.equals("лесенка") || rawCmd.equals("ladd")) {{
            if (parts.length > 1 && (parts[1].equalsIgnoreCase("stop") || parts[1].equalsIgnoreCase("стоп") || parts[1].equalsIgnoreCase("off"))) {{
                activeCancels.put(peer, true);
                AndroidUtilities.runOnUIThread(() -> {{
                    SendMessagesHelper.getInstance(account).sendMessage(
                        "🛑 Лесенка Pomoshgram остановлена!", peer, null, null, null, true, null, null, null, true, 0, null, false
                    );
                }});
                return true;
            }}

            String customText = "";
            if (parts.length > 1) {{
                int firstSpace = trimmed.indexOf(' ');
                if (firstSpace != -1) {{
                    customText = trimmed.substring(firstSpace).trim();
                }}
            }}

            final String fixedText = customText;
            activeCancels.put(peer, false);

            new Thread(() -> {{
                Random rand = new Random();
                while (!Boolean.TRUE.equals(activeCancels.get(peer))) {{
                    String phrase = (!fixedText.isEmpty()) ? fixedText : LADDER_PHRASES[rand.nextInt(LADDER_PHRASES.length)];
                    String[] words = phrase.split("\\\\s+");
                    for (String word : words) {{
                        if (Boolean.TRUE.equals(activeCancels.get(peer))) {{
                            return;
                        }}
                        AndroidUtilities.runOnUIThread(() -> {{
                            SendMessagesHelper.getInstance(account).sendMessage(
                                word, peer, replyToMsg, null, null, true, null, null, null, true, 0, null, false
                            );
                        }});
                        try {{
                            Thread.sleep(ladderSpeedMs);
                        }} catch (InterruptedException ignored) {{
                            return;
                        }}
                    }}
                    if (!fixedText.isEmpty()) {{
                        break;
                    }}
                    try {{
                        Thread.sleep(500);
                    }} catch (InterruptedException ignored) {{
                        return;
                    }}
                }}
            }}).start();
            return true;
        }}

        // 2. .stop / .стоп / .stop_spam (Instant Emergency Abort)
        if (rawCmd.equals("stop") || rawCmd.equals("стоп") || rawCmd.equals("stop_spam") || rawCmd.equals("stopspam")) {{
            activeCancels.put(peer, true);
            chatTargets.remove(peer);
            chatTargetNames.remove(peer);
            AndroidUtilities.runOnUIThread(() -> {{
                SendMessagesHelper.getInstance(account).sendMessage(
                    "🛑 Все активные атаки, лесенки и спам Pomoshgram ОСТАНОВЛЕНЫ!", peer, null, null, null, true, null, null, null, true, 0, null, false
                );
            }});
            return true;
        }}

        // 3. .aut_troll / .a_troll / .troll / .тролль (Continuous Savage Troll until .stop)
        if (rawCmd.equals("aut_troll") || rawCmd.equals("a_troll") || rawCmd.equals("troll") || rawCmd.equals("тролль")) {{
            if (parts.length > 1 && (parts[1].equalsIgnoreCase("off") || parts[1].equalsIgnoreCase("stop") || parts[1].equalsIgnoreCase("стоп"))) {{
                chatTargets.remove(peer);
                chatTargetNames.remove(peer);
                activeCancels.put(peer, true);
                AndroidUtilities.runOnUIThread(() -> {{
                    SendMessagesHelper.getInstance(account).sendMessage(
                        "✅ Режим «Тролль / Нейрохам» (.aut_troll) ВЫКЛЮЧЕН!", peer, null, null, null, true, null, null, null, true, 0, null, false
                    );
                }});
                return true;
            }}

            long targetId = 0;
            String targetName = "Жертва";
            if (replyToMsg != null) {{
                long sId = replyToMsg.getFromChatId();
                TLRPC.User u = MessagesController.getInstance(account).getUser(sId);
                if (u != null && u.first_name != null) {{
                    targetName = u.first_name;
                }}
                targetId = sId;
            }} else if (parts.length > 1) {{
                targetName = parts[1];
            }}

            chatTargets.put(peer, targetId);
            chatTargetNames.put(peer, targetName);
            activeCancels.put(peer, false);

            final String card = "🎯 ЦЕЛЬ ВЗЯТА НА ПРИЦЕЛ (Pomoshgram) 😈\\n\\n" +
                "👤 Цель: " + targetName + "\\n" +
                "🔥 Режим: Непрерывный разнос (375 панчей + Злой Нейрохам)\\n" +
                "🛑 Стоп: напиши .stop в чат";

            AndroidUtilities.runOnUIThread(() -> {{
                SendMessagesHelper.getInstance(account).sendMessage(
                    card, peer, replyToMsg, null, null, true, null, null, null, true, 0, null, false
                );
            }});

            new Thread(() -> {{
                Random rand = new Random();
                try {{
                    Thread.sleep(600);
                }} catch (InterruptedException ignored) {{}}

                while (!Boolean.TRUE.equals(activeCancels.get(peer)) && chatTargets.containsKey(peer)) {{
                    final String punch = PUNCHES[rand.nextInt(PUNCHES.length)];
                    AndroidUtilities.runOnUIThread(() -> {{
                        SendMessagesHelper.getInstance(account).sendMessage(
                            punch, peer, replyToMsg, null, null, true, null, null, null, true, 0, null, false
                        );
                    }});
                    try {{
                        Thread.sleep(750);
                    }} catch (InterruptedException ignored) {{
                        return;
                    }}
                }}
            }}).start();
            return true;
        }}

        // 4. .spam / .спам <count> [text]
        if (rawCmd.equals("spam") || rawCmd.equals("спам")) {{
            int count = 5;
            String spamText = "";
            if (parts.length >= 3) {{
                try {{
                    count = Integer.parseInt(parts[1]);
                    int idx = trimmed.indexOf(parts[1]);
                    spamText = trimmed.substring(idx + parts[1].length()).trim();
                }} catch (NumberFormatException e) {{
                    try {{
                        count = Integer.parseInt(parts[parts.length - 1]);
                        spamText = trimmed.substring(trimmed.indexOf(' '), trimmed.lastIndexOf(' ')).trim();
                    }} catch (Exception ex) {{
                        spamText = trimmed.substring(trimmed.indexOf(' ')).trim();
                    }}
                }}
            }} else if (parts.length == 2) {{
                try {{
                    count = Integer.parseInt(parts[1]);
                }} catch (NumberFormatException e) {{
                    spamText = parts[1];
                }}
            }}

            if (count > 50) count = 50;
            activeCancels.put(peer, false);
            final int finalCount = count;
            final String finalSpamText = spamText;

            new Thread(() -> {{
                Random rand = new Random();
                for (int i = 0; i < finalCount; i++) {{
                    if (Boolean.TRUE.equals(activeCancels.get(peer))) {{
                        return;
                    }}
                    final String msg = finalSpamText.isEmpty() ? PUNCHES[rand.nextInt(PUNCHES.length)] : finalSpamText;
                    AndroidUtilities.runOnUIThread(() -> {{
                        SendMessagesHelper.getInstance(account).sendMessage(
                            msg, peer, replyToMsg, null, null, true, null, null, null, true, 0, null, false
                        );
                    }});
                    try {{
                        Thread.sleep(320);
                    }} catch (InterruptedException ignored) {{
                        return;
                    }}
                }}
            }}).start();
            return true;
        }}

        // 5. .ping / .пинг
        if (rawCmd.equals("ping") || rawCmd.equals("пинг")) {{
            AndroidUtilities.runOnUIThread(() -> {{
                SendMessagesHelper.getInstance(account).sendMessage(
                    "🏓 Pomoshgram Client: В сети 24/7 | Pong! 🚀", peer, replyToMsg, null, null, true, null, null, null, true, 0, null, false
                );
            }});
            return true;
        }}

        // 6. .help / .помощь
        if (rawCmd.equals("help") || rawCmd.equals("помощь") || rawCmd.equals("cmds")) {{
            final String helpMsg = "⚡ КОМАНДЫ ЮЗЕРБОТА POMOSHGRAM:\\n\\n" +
                "🪜 .ladder [текст] — Бесконечная лесенка по словам до .stop\\n" +
                "😈 .aut_troll — Непрерывный авто-троллинг жертвы по реплаю\\n" +
                "🛑 .stop — Моментальная остановка всех атак и лесенок\\n" +
                "💣 .spam <кол-во> <текст> — Быстрый спам\\n" +
                "🏓 .ping — Проверка отклика клиента\\n" +
                "👻 Режим призрака и Premium-эмодзи папок активны всегда!";

            AndroidUtilities.runOnUIThread(() -> {{
                SendMessagesHelper.getInstance(account).sendMessage(
                    helpMsg, peer, replyToMsg, null, null, true, null, null, null, true, 0, null, false
                );
            }});
            return true;
        }}

        return false;
    }}
}}
'''

put_file(
    'TMessagesProj/src/main/java/com/pomoshgram/PomoshEngine.java',
    pomosh_engine_code.encode('utf-8'),
    'feat(pomoshgram): add PomoshEngine v2 with infinite continuous ladder, troll, stop, spam'
)

print("=== 9. Update .github/workflows/release.yml ===")
release_workflow = """name: Build Pomoshgram APK
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

          import android.util.Pair;
          import android.util.SparseArray;
          import org.telegram.messenger.MessageObject;
          import java.util.ArrayList;

          public class AyuHistoryHook {
              public static Pair<Integer, Integer> getMinAndMaxIds(ArrayList<MessageObject> messArr) {
                  if (messArr == null || messArr.isEmpty()) {
                      return new Pair<>(0, 0);
                  }
                  int min = Integer.MAX_VALUE;
                  int max = Integer.MIN_VALUE;
                  for (MessageObject msg : messArr) {
                      if (msg != null) {
                          int id = msg.getId();
                          if (id < min) min = id;
                          if (id > max) max = id;
                      }
                  }
                  if (min == Integer.MAX_VALUE) min = 0;
                  if (max == Integer.MIN_VALUE) max = 0;
                  return new Pair<>(min, max);
              }

              public static void doHook(int currentAccount, ArrayList<MessageObject> messArr, SparseArray<MessageObject>[] messagesDict, int startId, int endId, long dialogId, int limit, int topicId, boolean isSecretChat) {
              }
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
                      if (msg.peer_id != null) {
                          entity.peerId = MessageObject.getPeerId(msg.peer_id);
                      }
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

put_file(
    '.github/workflows/release.yml',
    release_workflow.encode('utf-8'),
    'ci(pomoshgram): configure automated pure 64-bit Pomoshgram build with Java 17 and NDK 21'
)

print("=== 10. Trigger Workflow Dispatch ===")
disp_url = f"https://api.github.com/repos/{REPO}/actions/workflows/release.yml/dispatches"
disp_payload = json.dumps({'ref': BRANCH}).encode('utf-8')
disp_req = urllib.request.Request(disp_url, data=disp_payload, headers=HEADERS, method='POST')
with urllib.request.urlopen(disp_req) as resp:
    print(f"Workflow build successfully triggered! Status: {resp.status}")

print("\n🚀 All Pomoshgram v2 updates pushed and build dispatched successfully!")
