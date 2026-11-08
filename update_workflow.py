import requests
import base64

TOKEN = "GIT_SECRET_TOKEN_REMOVED"
HEADERS = {"Authorization": f"token {TOKEN}"}

url = "https://api.github.com/repos/AUser7742/Pomoshgram/contents/.github/workflows/release.yml"
r = requests.get(url, headers=HEADERS)
sha = r.json()["sha"]

content = """name: Build Pomoshgram APK
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
          sudo apt-get install bison gcc make curl ninja-build ccache -y

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

data = {
    "message": "ci(pomoshgram): upgrade actions to v4 (checkout, setup-java, upload-artifact)",
    "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
    "sha": sha,
    "branch": "rewrite"
}

r2 = requests.put(url, headers=HEADERS, json=data)
print("Update status:", r2.status_code)
if r2.status_code in [200, 201]:
    print("Updated release.yml to v4 actions!")
