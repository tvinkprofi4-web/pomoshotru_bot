import requests
import base64
import json
import re

TOKEN = "GIT_SECRET_TOKEN_REMOVED"
REPO = "AUser7742/Pomoshgram"
BRANCH = "rewrite"
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json"
}

def get_file_sha(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r.json().get("sha")
    return None

def put_file(path, content_bytes, commit_message):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    sha = get_file_sha(path)
    data = {
        "message": commit_message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": BRANCH
    }
    if sha:
        data["sha"] = sha
    r = requests.put(url, headers=HEADERS, json=data)
    if r.status_code in [200, 201]:
        print(f"[OK] {path} updated! (Commit: {r.json().get('commit', {}).get('sha', '')[:7]})")
        return True
    else:
        print(f"[ERROR] {path} failed: {r.status_code} - {r.text[:300]}")
        return False

# 1. Parse TROLL_LADDER_PHRASES and TROLL_PUNCHES from bot.py
with open(r"c:\Users\user\Desktop\pomoshotru_bot\bot.py", "r", encoding="utf-8") as f:
    bot_code = f.read()

ladder_m = re.search(r'TROLL_LADDER_PHRASES\s*=\s*\[(.*?)\]\n\n', bot_code, re.DOTALL)
ladder_list = []
if ladder_m:
    ladder_list = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', ladder_m.group(1))

punches_m = re.search(r'TROLL_PUNCHES\s*=\s*\[(.*?)\]\n\n', bot_code, re.DOTALL)
punches_list = []
if punches_m:
    punches_list = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', punches_m.group(1))

if not ladder_list:
    ladder_list = ["Соси молча и не пищи", "Слюни подбери пока зубы целы", "В будку обратно залезь животное"]
if not punches_list:
    punches_list = ["Ты ошибся планетой, клоун", "Твой голос здесь не имеет веса", "Иди уроки делай"]

print(f"Extracted {len(ladder_list)} ladder phrases, {len(punches_list)} punches.")

def escape_java(s):
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '')

ladder_java_items = ',\n        '.join(f'"{escape_java(p)}"' for p in ladder_list[:100])
punches_java_items = ',\n        '.join(f'"{escape_java(p)}"' for p in punches_list[:100])

pomosh_engine_code = f'''package com.pomoshgram;

import android.text.TextUtils;
import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.MessageObject;
import org.telegram.messenger.SendMessagesHelper;

import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;

public class PomoshEngine {{

    public static volatile boolean enabled = true;
    public static volatile int ladderSpeedMs = 280;
    public static final ConcurrentHashMap<Long, Boolean> activeCancels = new ConcurrentHashMap<>();
    public static final ConcurrentHashMap<Long, Long> chatTargets = new ConcurrentHashMap<>();
    public static final ConcurrentHashMap<Long, String> chatTargetNames = new ConcurrentHashMap<>();

    public static final String[] LADDER_PHRASES = new String[] {{
        {ladder_java_items}
    }};

    public static final String[] PUNCHES = new String[] {{
        {punches_java_items}
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

        // 1. .ladder / .лесенка
        if (rawCmd.equals("ladder") || rawCmd.equals("лесенка") || rawCmd.equals("ladd")) {{
            if (parts.length > 1 && (parts[1].equalsIgnoreCase("stop") || parts[1].equalsIgnoreCase("стоп") || parts[1].equalsIgnoreCase("off"))) {{
                activeCancels.put(peer, true);
                return true;
            }}

            String customText = "";
            if (parts.length > 1) {{
                int firstSpace = trimmed.indexOf(' ');
                if (firstSpace != -1) {{
                    customText = trimmed.substring(firstSpace).trim();
                }}
            }}

            final String phraseToSend;
            if (!customText.isEmpty()) {{
                phraseToSend = customText;
            }} else {{
                Random rand = new Random();
                phraseToSend = LADDER_PHRASES[rand.nextInt(LADDER_PHRASES.length)];
            }}

            activeCancels.put(peer, false);
            final String[] words = phraseToSend.split("\\\\s+");

            new Thread(() -> {{
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
            }}).start();
            return true;
        }}

        // 2. .stop / .стоп / .stop_spam
        if (rawCmd.equals("stop") || rawCmd.equals("стоп") || rawCmd.equals("stop_spam") || rawCmd.equals("stopspam")) {{
            activeCancels.put(peer, true);
            return true;
        }}

        // 3. .a_troll / .troll / .тролль
        if (rawCmd.equals("a_troll") || rawCmd.equals("troll") || rawCmd.equals("тролль")) {{
            if (parts.length > 1 && (parts[1].equalsIgnoreCase("off") || parts[1].equalsIgnoreCase("stop") || parts[1].equalsIgnoreCase("стоп"))) {{
                chatTargets.remove(peer);
                chatTargetNames.remove(peer);
                AndroidUtilities.runOnUIThread(() -> {{
                    SendMessagesHelper.getInstance(account).sendMessage(
                        "✅ Режим «Тролль / Нейрохам» (.a_troll) ВЫКЛЮЧЕН!", peer, null, null, null, true, null, null, null, true, 0, null, false
                    );
                }});
                return true;
            }}

            long targetId = 0;
            String targetName = "Жертва";
            if (replyToMsg != null && replyToMsg.messageOwner != null && replyToMsg.messageOwner.from_id != null) {{
                targetId = replyToMsg.messageOwner.from_id.user_id;
                targetName = replyToMsg.getSenderName();
            }}

            if (targetId == 0 && parts.length > 1) {{
                targetName = parts[1];
            }}

            if (targetId != 0 || !targetName.equals("Жертва")) {{
                chatTargets.put(peer, targetId);
                chatTargetNames.put(peer, targetName);

                final String card = "🎯 ЦЕЛЬ ВЗЯТА НА ПРИЦЕЛ (Pomoshgram) 😈\\n\\n" +
                    "🎯 Жертва: " + targetName + "\\n" +
                    "😈 Режим атаки: Злой Нейрохам (NullSecAI)\\n\\n" +
                    "🔥 Клиент будет разносить каждое сообщение этой цели!\\n" +
                    "🛑 Снять: .a_troll off или .stop";

                AndroidUtilities.runOnUIThread(() -> {{
                    SendMessagesHelper.getInstance(account).sendMessage(
                        card, peer, replyToMsg, null, null, true, null, null, null, true, 0, null, false
                    );
                }});

                Random rand = new Random();
                final String firstPunch = PUNCHES[rand.nextInt(PUNCHES.length)];
                new Thread(() -> {{
                    try {{
                        Thread.sleep(400);
                    }} catch (InterruptedException ignored) {{}}
                    AndroidUtilities.runOnUIThread(() -> {{
                        SendMessagesHelper.getInstance(account).sendMessage(
                            firstPunch, peer, replyToMsg, null, null, true, null, null, null, true, 0, null, false
                        );
                    }});
                }}).start();
            }}
            return true;
        }}

        // 4. .spam / .спам
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
                        Thread.sleep(350);
                    }} catch (InterruptedException ignored) {{
                        return;
                    }}
                }}
            }}).start();
            return true;
        }}

        // 5. .ping
        if (rawCmd.equals("ping") || rawCmd.equals("пинг")) {{
            AndroidUtilities.runOnUIThread(() -> {{
                SendMessagesHelper.getInstance(account).sendMessage(
                    "🏓 Pomoshgram Client: В сети 24/7 | Pong!", peer, replyToMsg, null, null, true, null, null, null, true, 0, null, false
                );
            }});
            return true;
        }}

        return false;
    }}
}}
'''

print("Uploading PomoshEngine.java...")
put_file(
    "TMessagesProj/src/main/java/com/pomoshgram/PomoshEngine.java",
    pomosh_engine_code.encode("utf-8"),
    "feat(pomoshgram): add PomoshEngine userbot commands handler (.ladder, .a_troll, .spam, .stop)"
)

# 2. Update SendMessagesHelper.java
print("Fetching SendMessagesHelper.java...")
r_smh = requests.get(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java")
smh_text = r_smh.text

target_anchor = "        // --- AyuGram hook\n\n        String originalPath = null;"
replacement_hook = """        // --- AyuGram hook

        // --- Pomoshgram Userbot Hook
        if (com.pomoshgram.PomoshEngine.handleOutgoingMessage(currentAccount, message, peer, replyToMsg)) {
            return;
        }

        String originalPath = null;"""

if target_anchor in smh_text:
    smh_text = smh_text.replace(target_anchor, replacement_hook)
    print("Hooking SendMessagesHelper.java...")
    put_file(
        "TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java",
        smh_text.encode("utf-8"),
        "feat(pomoshgram): hook PomoshEngine into SendMessagesHelper.sendMessage"
    )
else:
    print("Warning: target anchor not found in SendMessagesHelper.java")

# 3. Update AyuConstants.java
print("Fetching AyuConstants.java...")
r_const = requests.get(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/TMessagesProj/src/main/java/com/radolyn/ayugram/AyuConstants.java")
const_text = r_const.text
const_text = const_text.replace('public static String APP_NAME = "AyuGram";', 'public static String APP_NAME = "Pomoshgram";')
const_text = const_text.replace('public static String APP_GITHUB = "AyuGram/AyuGram4A";', f'public static String APP_GITHUB = "{REPO}";')
put_file(
    "TMessagesProj/src/main/java/com/radolyn/ayugram/AyuConstants.java",
    const_text.encode("utf-8"),
    "feat(pomoshgram): rename APP_NAME to Pomoshgram"
)

# 4. Update strings.xml AppName
print("Fetching strings.xml...")
r_str = requests.get(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/TMessagesProj/src/main/res/values/strings.xml")
str_text = r_str.text
str_text = str_text.replace('<string name="AppName">Telegram</string>', '<string name="AppName">Pomoshgram</string>')
str_text = str_text.replace('<string name="AppNameBeta">Telegram Beta</string>', '<string name="AppNameBeta">Pomoshgram</string>')
put_file(
    "TMessagesProj/src/main/res/values/strings.xml",
    str_text.encode("utf-8"),
    "feat(pomoshgram): set AppName to Pomoshgram in strings.xml"
)

# 5. Update .github/workflows/release.yml to build on ubuntu-latest and output Pomoshgram.apk
release_workflow = """name: Build Pomoshgram APK
on:
  push:
    branches:
      - rewrite
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    env:
      CCACHE_COMPILERCHECK: "%compiler% -dumpmachine; %compiler% -dumpversion"
      CCACHE_NOHASHDIR: "true"
      CCACHE_MAXSIZE: "10G"
      CCACHE_HARDLINK: "true"
    steps:
      - uses: actions/checkout@v3
        with:
          submodules: recursive
          fetch-depth: 0

      - name: Create API_KEYS & Keystore
        run: |
          mkdir -p TMessagesProj/config
          keytool -genkey -v -keystore TMessagesProj/config/extera.jks -alias pomosh -keyalg RSA -keysize 2048 -validity 10000 -storepass pomoshpassword -keypass pomoshpassword -dname "CN=Pomoshgram, OU=Dev, O=Pomoshgram, L=Tashkent, S=Tashkent, C=UZ"
          cat << 'EOF' > ./API_KEYS
          APP_ID = 6
          APP_HASH = "eb06d4abfb49dc3eeb1aeb98ae0f581e"
          MAPS_V2_API = ""
          
          SIGNING_KEY_PASSWORD = "pomoshpassword"
          SIGNING_KEY_ALIAS = "pomosh"
          SIGNING_KEY_STORE_PASSWORD = "pomoshpassword"
          EOF

      - name: Setup Java
        uses: actions/setup-java@v3
        with:
          distribution: 'temurin'
          java-version: '17'
          cache: 'gradle'

      - name: Set up ccache
        uses: hendrikmuhs/ccache-action@v1.2
        with:
          key: ccache
          restore-keys: ccache

      - name: Setup Android SDK Tools
        uses: android-actions/setup-android@v2

      - name: Free Disk Space
        run: |
          sudo rm -rf /usr/share/dotnet/
          sudo rm -rf /usr/local/graalvm/
          sudo rm -rf /usr/local/.ghcup/
          sudo rm -rf /usr/local/share/powershell
          sudo rm -rf /usr/local/share/chromium
          sudo rm -rf /usr/local/lib/node_modules
          sudo apt-get install bison gcc make curl ninja-build ccache -y

      - name: Grant execute permission for gradlew
        run: chmod +x gradlew

      - name: Build Pomoshgram APK
        run: ./gradlew assembleAfatRelease

      - name: Upload Pomoshgram APK Artifact
        uses: actions/upload-artifact@v3
        with:
          name: Pomoshgram-Release-APK
          path: TMessagesProj/build/outputs/apk/afat/release/*.apk
"""

print("Updating .github/workflows/release.yml...")
put_file(
    ".github/workflows/release.yml",
    release_workflow.encode("utf-8"),
    "ci(pomoshgram): configure automated GitHub Actions build for Pomoshgram.apk on ubuntu-latest"
)

print("\nALL POMOSHGRAM FILES DEPLOYED TO GITHUB!")
