import urllib.request
import json
import base64

TOKEN = 'GIT_SECRET_TOKEN_REMOVED'
headers = {
    'Authorization': f'token {TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'Pomosh'
}

# 1. Delete .gitmodules
try:
    url = 'https://api.github.com/repos/AUser7742/Pomoshgram/contents/.gitmodules?ref=rewrite'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        sha = data['sha']
    
    del_payload = json.dumps({
        'message': 'ci(pomoshgram): remove broken proprietary submodule',
        'sha': sha,
        'branch': 'rewrite'
    }).encode('utf-8')
    del_req = urllib.request.Request(url, data=del_payload, headers=headers, method='DELETE')
    with urllib.request.urlopen(del_req) as resp:
        print('.gitmodules deleted:', resp.status)
except Exception as e:
    print('Delete .gitmodules error (may already be deleted):', e)

# 2. Update release.yml
new_workflow = """name: Build Pomoshgram APK
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
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Create API_KEYS & Keystore & Stubs
        run: |
          mkdir -p TMessagesProj/config
          mkdir -p TMessagesProj/src/main/java/com/radolyn/ayugram/proprietary
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
        uses: actions/setup-java@v4
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
        uses: android-actions/setup-android@v3

      - name: Free Disk Space
        run: |
          sudo rm -rf /usr/share/dotnet/
          sudo rm -rf /usr/local/graalvm/
          sudo rm -rf /usr/local/.ghcup/
          sudo rm -rf /usr/local/share/powershell
          sudo rm -rf /usr/local/share/chromium
          sudo rm -rf /usr/local/lib/node_modules
          sudo apt-get update && sudo apt-get install bison gcc make curl ninja-build ccache -y

      - name: Grant execute permission for gradlew
        run: chmod +x gradlew

      - name: Build Pomoshgram APK
        run: ./gradlew assembleAfatRelease

      - name: Upload Pomoshgram APK Artifact
        uses: actions/upload-artifact@v4
        with:
          name: Pomoshgram-Release-APK
          path: TMessagesProj/build/outputs/apk/afat/release/*.apk
"""

url_wf = 'https://api.github.com/repos/AUser7742/Pomoshgram/contents/.github/workflows/release.yml?ref=rewrite'
req_wf = urllib.request.Request(url_wf, headers=headers)
with urllib.request.urlopen(req_wf) as resp:
    data_wf = json.loads(resp.read().decode())
    wf_sha = data_wf['sha']

put_payload = json.dumps({
    'message': 'ci(pomoshgram): remove submodules requirement from checkout',
    'content': base64.b64encode(new_workflow.encode('utf-8')).decode('utf-8'),
    'sha': wf_sha,
    'branch': 'rewrite'
}).encode('utf-8')

put_req = urllib.request.Request(url_wf, data=put_payload, headers=headers, method='PUT')
with urllib.request.urlopen(put_req) as resp:
    print('release.yml updated:', resp.status)

# 3. Trigger workflow dispatch
disp_url = 'https://api.github.com/repos/AUser7742/Pomoshgram/actions/workflows/release.yml/dispatches'
disp_payload = json.dumps({'ref': 'rewrite'}).encode('utf-8')
disp_req = urllib.request.Request(disp_url, data=disp_payload, headers=headers, method='POST')
with urllib.request.urlopen(disp_req) as resp:
    print('Workflow dispatched:', resp.status)
