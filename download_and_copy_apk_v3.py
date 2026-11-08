import os
import sys
import time
import json
import urllib.request
import zipfile
import io

TOKEN = 'GIT_SECRET_TOKEN_REMOVED'
REPO = 'tvinkprofi4-web/Pomoshgram'
RUN_ID = '41338825648'
HEADERS = {
    'Authorization': f'token {TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'Pomosh'
}

print(f"Monitoring GitHub Actions run {RUN_ID} on {REPO}...", flush=True)

class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if 'Authorization' in new_req.headers:
            del new_req.headers['Authorization']
        return new_req

opener = urllib.request.build_opener(NoAuthRedirect)

while True:
    try:
        url = f"https://api.github.com/repos/{REPO}/actions/runs/{RUN_ID}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode())
        
        status = data.get('status')
        conclusion = data.get('conclusion')
        print(f"[{time.strftime('%H:%M:%S')}] Status: {status}, Conclusion: {conclusion}", flush=True)
        
        if status == 'completed':
            if conclusion == 'success':
                print("[SUCCESS] Build passed! Downloading artifact...", flush=True)
                art_url = f"https://api.github.com/repos/{REPO}/actions/runs/{RUN_ID}/artifacts"
                req_art = urllib.request.Request(art_url, headers=HEADERS)
                with urllib.request.urlopen(req_art, timeout=25) as resp:
                    art_data = json.loads(resp.read().decode())
                
                artifacts = art_data.get('artifacts', [])
                if not artifacts:
                    print("No artifacts found!", flush=True)
                    break
                    
                download_url = artifacts[0]['archive_download_url']
                print(f"Downloading from {download_url}...", flush=True)
                req_dl = urllib.request.Request(download_url, headers=HEADERS)
                zip_bytes = opener.open(req_dl, timeout=120).read()
                
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                    for name in z.namelist():
                        if name.endswith('.apk'):
                            apk_data = z.read(name)
                            dest_path = r'c:\Users\user\Desktop\Pomoshgram.apk'
                            with open(dest_path, 'wb') as f_out:
                                f_out.write(apk_data)
                            print(f"[SAVED] Extracted {name} to {dest_path} ({len(apk_data)} bytes)", flush=True)
                            
                            # Create private draft release
                            rel_url = f"https://api.github.com/repos/{REPO}/releases"
                            payload = {
                                'tag_name': f'v{int(time.time())}',
                                'name': 'Pomoshgram Android Client (Private Draft)',
                                'body': 'Official Private Build of Pomoshgram with Custom Cyberpunk 3D Icon and 100% Rebrand.',
                                'draft': True,
                                'prerelease': False
                            }
                            req_rel = urllib.request.Request(rel_url, data=json.dumps(payload).encode('utf-8'), headers=HEADERS, method='POST')
                            try:
                                with urllib.request.urlopen(req_rel, timeout=25) as resp_rel:
                                    rel_json = json.loads(resp_rel.read().decode())
                                    print(f"[OK] Created private draft release: {rel_json.get('html_url')}", flush=True)
                            except Exception as e_rel:
                                print(f"[WARN] Failed to create draft release: {e_rel}", flush=True)
                            break
            else:
                print(f"Build failed with conclusion: {conclusion}", flush=True)
            break
    except Exception as e:
        print(f"Polling exception: {e}", flush=True)
    
    time.sleep(15)
