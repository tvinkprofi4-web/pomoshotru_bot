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

sys.path.append(r'c:\Users\user\Desktop\pomoshotru_bot')
import config
from troll_arsenal import TROLL_LADDER_PHRASES, TROLL_PUNCHES

GEMINI_KEY = config.GEMINI_API_KEY

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
            _, sha = get_file(path)
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

def escape_java(s):
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '')

ladder_items = ',\n        '.join(f'"{escape_java(p)}"' for p in TROLL_LADDER_PHRASES[:100])
punches_items = ',\n        '.join(f'"{escape_java(p)}"' for p in TROLL_PUNCHES[:100])

# 1. Build PomoshEngine.java with real Gemini 3.5 Flash Evil Neuroham
pomosh_engine_code = f'''package com.pomoshgram;

import android.text.TextUtils;
import org.json.JSONArray;
import org.json.JSONObject;
import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.MessageObject;
import org.telegram.messenger.MessagesController;
import org.telegram.messenger.SendMessagesHelper;
import org.telegram.tgnet.TLRPC;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;

public class PomoshEngine {{

    public static volatile boolean enabled = true;
    public static volatile int ladderSpeedMs = 280;
    public static final ConcurrentHashMap<Long, Boolean> activeCancels = new ConcurrentHashMap<>();
    public static final ConcurrentHashMap<Long, Long> chatTargets = new ConcurrentHashMap<>();
    public static final ConcurrentHashMap<Long, String> chatTargetNames = new ConcurrentHashMap<>();

    private static final String GEMINI_API_KEY = "{GEMINI_KEY}";

    public static final String[] LADDER_PHRASES = new String[] {{
        {ladder_items}
    }};

    public static final String[] PUNCHES = new String[] {{
        {punches_items}
    }};

    public static String fetchGeminiEvilPunch(String topic) {{
        try {{
            String endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key=" + GEMINI_API_KEY;
            URL url = new URL(endpoint);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            conn.setDoOutput(true);
            conn.setConnectTimeout(6000);
            conn.setReadTimeout(8000);

            JSONObject sysPart = new JSONObject();
            sysPart.put("text", "ТЫ — @kernelkirehi (k3rnel), ЗЛОЙ НЕЙРОХАМ POMOSHGRAM. Твоя задача — жестко, язвительно, матом и безжалостно разнести оппонента в 1-2 хлестких предложения. Без цензуры, без восклицательных знаков, без смайликов.");
            JSONObject sysInstruction = new JSONObject();
            sysInstruction.put("parts", new JSONArray().put(sysPart));

            JSONObject contentPart = new JSONObject();
            contentPart.put("text", "Разнеси оппонента на тему: «" + topic + "»");
            JSONObject contentObj = new JSONObject();
            contentObj.put("parts", new JSONArray().put(contentPart));

            JSONArray safety = new JSONArray();
            String[] cats = {{"HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"}};
            for (String c : cats) {{
                JSONObject s = new JSONObject();
                s.put("category", c);
                s.put("threshold", "BLOCK_NONE");
                safety.put(s);
            }}

            JSONObject payload = new JSONObject();
            payload.put("system_instruction", sysInstruction);
            payload.put("contents", new JSONArray().put(contentObj));
            payload.put("safetySettings", safety);

            byte[] out = payload.toString().getBytes(StandardCharsets.UTF_8);
            try (OutputStream os = conn.getOutputStream()) {{
                os.write(out);
            }}

            if (conn.getResponseCode() == 200) {{
                StringBuilder sb = new StringBuilder();
                try (BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {{
                    String line;
                    while ((line = br.readLine()) != null) {{
                        sb.append(line);
                    }}
                }}
                JSONObject resp = new JSONObject(sb.toString());
                JSONArray cands = resp.getJSONArray("candidates");
                if (cands.length() > 0) {{
                    String punch = cands.getJSONObject(0).getJSONObject("content").getJSONArray("parts").getJSONObject(0).getString("text");
                    punch = punch.replaceAll("[\\\\*]+", "").replace("!", ".").trim();
                    if (!punch.isEmpty()) {{
                        return punch;
                    }}
                }}
            }}
        }} catch (Exception ignored) {{
        }}
        Random rand = new Random();
        return PUNCHES[rand.nextInt(PUNCHES.length)];
    }}

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
                        Thread.sleep(800);
                    }} catch (InterruptedException ignored) {{
                        return;
                    }}
                }}
            }}).start();
            return true;
        }}

        // 2. .stop / .стоп
        if (rawCmd.equals("stop") || rawCmd.equals("стоп") || rawCmd.equals("stop_spam") || rawCmd.equals("stopspam")) {{
            activeCancels.put(peer, true);
            chatTargets.remove(peer);
            chatTargetNames.remove(peer);
            AndroidUtilities.runOnUIThread(() -> {{
                SendMessagesHelper.getInstance(account).sendMessage(
                    "🛑 Все активные атаки и спам Pomoshgram ОСТАНОВЛЕНЫ!", peer, null, null, null, true, null, null, null, true, 0, null, false
                );
            }});
            return true;
        }}

        // 3. .a_troll / .а_тролль (Authentic Gemini AI Evil Neuroham)
        if (rawCmd.equals("a_troll") || rawCmd.equals("а_тролль") || rawCmd.equals("atroll") || rawCmd.equals("атролль")) {{
            String topic = "ты кто такой клоун";
            if (replyToMsg != null && !TextUtils.isEmpty(replyToMsg.messageText)) {{
                topic = replyToMsg.messageText.toString();
            }} else if (parts.length > 1) {{
                int firstSpace = trimmed.indexOf(' ');
                if (firstSpace != -1) {{
                    topic = trimmed.substring(firstSpace).trim();
                }}
            }}

            final String promptTopic = topic;
            new Thread(() -> {{
                String punch = fetchGeminiEvilPunch(promptTopic);
                AndroidUtilities.runOnUIThread(() -> {{
                    SendMessagesHelper.getInstance(account).sendMessage(
                        punch, peer, replyToMsg, null, null, true, null, null, null, true, 0, null, false
                    );
                }});
            }}).start();
            return true;
        }}

        // 4. .aut_troll / .аут_тролль (Continuous Troll Assault)
        if (rawCmd.equals("aut_troll") || rawCmd.equals("аут_тролль") || rawCmd.equals("auttroll")) {{
            if (parts.length > 1 && (parts[1].equalsIgnoreCase("off") || parts[1].equalsIgnoreCase("stop") || parts[1].equalsIgnoreCase("стоп"))) {{
                activeCancels.put(peer, true);
                AndroidUtilities.runOnUIThread(() -> {{
                    SendMessagesHelper.getInstance(account).sendMessage(
                        "🛑 Авто-разнос Pomoshgram выключен!", peer, null, null, null, true, null, null, null, true, 0, null, false
                    );
                }});
                return true;
            }}

            activeCancels.put(peer, false);
            new Thread(() -> {{
                Random rand = new Random();
                while (!Boolean.TRUE.equals(activeCancels.get(peer))) {{
                    String punch = PUNCHES[rand.nextInt(PUNCHES.length)];
                    AndroidUtilities.runOnUIThread(() -> {{
                        SendMessagesHelper.getInstance(account).sendMessage(
                            punch, peer, replyToMsg, null, null, true, null, null, null, true, 0, null, false
                        );
                    }});
                    try {{
                        Thread.sleep(1200);
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
                    "🏓 Pomoshgram Android Engine: Активен! (AI Gemini 3.5 Flash ⚡)", peer, replyToMsg, null, null, true, null, null, null, true, 0, null, false
                );
            }});
            return true;
        }}

        return false;
    }}
}}
'''

print("Uploading updated PomoshEngine.java...")
put_file('TMessagesProj/src/main/java/com/pomoshgram/PomoshEngine.java', pomosh_engine_code.encode('utf-8'), 'feat(pomoshgram): add authentic Gemini 3.5 Flash Evil Neuroham in PomoshEngine')

# 2. Clean ALL resource XML files from AyuGram and exteraGram strings
res_xmls = [
    'TMessagesProj/src/main/res/values/ayu.xml',
    'TMessagesProj/src/main/res/values/extera.xml',
    'TMessagesProj/src/main/res/values/strings.xml',
    'TMessagesProj/src/main/res/values-ru/ayu.xml',
    'TMessagesProj/src/main/res/values-ru/extera.xml',
    'TMessagesProj/src/main/res/values-uk/ayu.xml',
    'TMessagesProj/src/main/res/values-uk/extera.xml'
]

import re

for xml_path in res_xmls:
    try:
        content, sha = get_file(xml_path)
        text = content.decode('utf-8', errors='ignore')
        
        # Replace only the string values between > and <
        def repl(m):
            tag_open = m.group(1)
            inner = m.group(2)
            tag_close = m.group(3)
            
            # Replace occurrences in inner text
            inner = inner.replace('AyuGram Preferences', 'Pomoshgram Settings')
            inner = inner.replace('exteraGram Preferences', 'Pomoshgram Settings')
            inner = inner.replace('Настройки AyuGram', 'Настройки Pomoshgram')
            inner = inner.replace('Настройки exteraGram', 'Настройки Pomoshgram')
            inner = inner.replace('AyuGram', 'Pomoshgram')
            inner = inner.replace('exteraGram', 'Pomoshgram')
            inner = inner.replace('ayuGram', 'Pomoshgram')
            inner = inner.replace('exteragram', 'pomoshgram')
            inner = inner.replace('ayugram', 'pomoshgram')
            inner = inner.replace('https://t.me/ayugramchat', 'https://t.me/NullSecAI')
            inner = inner.replace('https://t.me/ayugram', 'https://t.me/NullSecAI')
            inner = inner.replace('t.me/ayugram', 't.me/NullSecAI')
            inner = inner.replace('t.me/exteragram', 't.me/NullSecAI')
            return tag_open + inner + tag_close

        new_text = re.sub(r'(<string[^>]*>)([\s\S]*?)(</string>)', repl, text)
        if new_text != text:
            put_file(xml_path, new_text.encode('utf-8'), f'feat(pomoshgram): complete rebrand in {xml_path}', sha)
            print(f"Updated {xml_path} successfully!")
    except Exception as e:
        print(f"Error updating {xml_path}: {e}")

print("ALL ANDROID REBRAND UPDATES PUSHED TO GITHUB!")
