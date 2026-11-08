import re

with open(r'c:\Users\user\Desktop\pomoshotru_bot\premium_client.py', 'r', encoding='utf-8') as f:
    code = f.read()

matches = re.findall(r'(?:if|elif)\s+cmd\s+in\s+\[(.*?)\]', code)
cmds = []
for m in matches:
    parts = [x.strip().strip("'\"") for x in m.split(',') if x.strip()]
    cmds.extend(parts)

print("Commands found in premium_client.py:")
for c in sorted(list(set(cmds))):
    if c:
        print(f"  .{c}")

# Let's also check function definitions
funcs = re.findall(r'async def _run_userbot_([a-zA-Z0-9_]+)', code)
print("\nUserbot functions found:")
for fn in funcs:
    print(f"  _run_userbot_{fn}")
