import requests, base64

token = 'GIT_SECRET_TOKEN_REMOVED'
headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github.v3+json'}
repo = 'tvinkprofi4-web/Pomoshgram'
branch = 'rewrite'

url = f'https://api.github.com/repos/{repo}/contents/TMessagesProj/src/main/java/com/pomoshgram/PomoshEngine.java?ref={branch}'
r = requests.get(url, headers=headers)
data = r.json()
sha = data['sha']
content = base64.b64decode(data['content']).decode('utf-8')

# Replace the broken threshold line
lines = content.splitlines()
fixed_lines = []
found = False
for line in lines:
    if 'HARM_CATEGORY_HARASSMENT' in line:
        fixed_lines.append('                "{\\"category\\":\\"HARM_CATEGORY_HARASSMENT\\",\\"threshold\\":\\"BLOCK_NONE\\"}," +')
        found = True
    else:
        fixed_lines.append(line)

new_content = '\n'.join(fixed_lines)
print('Replaced line:', found)

payload = {
    'message': 'fix(engine): remove illegal escape sequence in PomoshEngine.java',
    'content': base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
    'sha': sha,
    'branch': branch
}
r_put = requests.put(f'https://api.github.com/repos/{repo}/contents/TMessagesProj/src/main/java/com/pomoshgram/PomoshEngine.java', headers=headers, json=payload)
print('Pushed fix to GitHub:', r_put.status_code)

disp_url = f'https://api.github.com/repos/{repo}/actions/workflows/release.yml/dispatches'
r_disp = requests.post(disp_url, headers=headers, json={'ref': branch})
print('Workflow dispatched:', r_disp.status_code)
