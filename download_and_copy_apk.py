import urllib.request
import json
import time
import zipfile
import io
import os
import shutil

TOKEN = 'GIT_SECRET_TOKEN_REMOVED'
HEADERS = {
    'Authorization': f'token {TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'Pomosh'
}

RUN_ID = 41328927352
REPO = 'AUser7742/Pomoshgram'
DESKTOP_PATH = r'c:\Users\user\Desktop'
TARGET_APK = os.path.join(DESKTOP_PATH, 'Pomoshgram.apk')

class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req and 'Authorization' in new_req.headers:
            del new_req.headers['Authorization']
        return new_req

opener = urllib.request.build_opener(NoAuthRedirect)

print(f"Monitoring GitHub Actions run {RUN_ID}...", flush=True)

def create_github_release(apk_path):
    try:
        tag_name = f"v1.0-{int(time.time())}"
        rel_url = f"https://api.github.com/repos/{REPO}/releases"
        rel_data = {
            "tag_name": tag_name,
            "target_commitish": "rewrite",
            "name": "Pomoshgram v1.0",
            "body": "Pomoshgram Android Client with native PomoshEngine userbot (.ladder, .a_troll, .spam, .stop, .ping). Zero server required.",
            "draft": False,
            "prerelease": False
        }
        req = urllib.request.Request(rel_url, data=json.dumps(rel_data).encode('utf-8'), headers=HEADERS, method='POST')
        with urllib.request.urlopen(req) as resp:
            rel_resp = json.loads(resp.read().decode())
            upload_url = rel_resp['upload_url'].split('{')[0]
            print(f"Created GitHub Release: {rel_resp['html_url']}", flush=True)
            
        # Upload APK asset
        asset_url = f"{upload_url}?name=Pomoshgram.apk"
        with open(apk_path, 'rb') as f:
            apk_bytes = f.read()
            
        up_headers = {
            'Authorization': f'token {TOKEN}',
            'Content-Type': 'application/vnd.android.package-archive',
            'User-Agent': 'Pomosh'
        }
        up_req = urllib.request.Request(asset_url, data=apk_bytes, headers=up_headers, method='POST')
        with urllib.request.urlopen(up_req) as resp:
            asset_resp = json.loads(resp.read().decode())
            print(f"Uploaded APK to Release: {asset_resp['browser_download_url']}", flush=True)
            
    except Exception as e:
        print(f"Notice: Release creation optional step error: {e}", flush=True)

while True:
    try:
        url = f'https://api.github.com/repos/{REPO}/actions/runs/{RUN_ID}'
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            status = data.get('status')
            conclusion = data.get('conclusion')
            
        print(f"[{time.strftime('%H:%M:%S')}] Status: {status}, Conclusion: {conclusion}", flush=True)
        
        if status == 'completed':
            if conclusion == 'success':
                print("Build succeeded! Fetching artifacts...", flush=True)
                art_url = f'https://api.github.com/repos/{REPO}/actions/runs/{RUN_ID}/artifacts'
                art_req = urllib.request.Request(art_url, headers=HEADERS)
                with urllib.request.urlopen(art_req) as resp:
                    art_data = json.loads(resp.read().decode())
                
                artifacts = art_data.get('artifacts', [])
                if not artifacts:
                    print("Error: No artifacts found!", flush=True)
                    break
                
                artifact = artifacts[0]
                download_url = artifact['archive_download_url']
                print(f"Downloading artifact '{artifact['name']}' ({artifact['size_in_bytes']} bytes)...", flush=True)
                
                dl_req = urllib.request.Request(download_url, headers=HEADERS)
                with opener.open(dl_req) as resp:
                    zip_bytes = resp.read()
                
                print("Download complete. Extracting APK...", flush=True)
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                    for name in z.namelist():
                        if name.endswith('.apk'):
                            print(f"Found APK: {name}", flush=True)
                            with z.open(name) as src, open(TARGET_APK, 'wb') as dst:
                                shutil.copyfileobj(src, dst)
                            print(f"SUCCESS: Saved APK to {TARGET_APK} ({os.path.getsize(TARGET_APK)} bytes)", flush=True)
                            create_github_release(TARGET_APK)
                            break
                    else:
                        print(f"Contents of zip: {z.namelist()}", flush=True)
                        first_file = z.namelist()[0]
                        with z.open(first_file) as src, open(TARGET_APK, 'wb') as dst:
                            shutil.copyfileobj(src, dst)
                        print(f"Extracted {first_file} to {TARGET_APK}", flush=True)
                        create_github_release(TARGET_APK)
                break
            else:
                print(f"Build failed with conclusion: {conclusion}", flush=True)
                break
                
    except Exception as e:
        print(f"Error during check: {e}", flush=True)
        
    time.sleep(20)
