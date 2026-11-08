with open(r'C:\Users\user\Desktop\pomoshotru_bot\bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# line 11801 is:
#             if is_group and dot_cmd in ["ladder", ...]:
#             return
#         if dot_cmd in ["only", ...]:

for i in range(11790, min(11815, len(lines))):
    if 'if is_group and dot_cmd in ["ladder"' in lines[i]:
        # Fix the indentation of the return on next line and the if on the following line
        lines[i] = '            if dot_cmd in ["ladder", "лесенка", "ladd", "ладдер", "aut_ladder", "автолесенка", "spam", "спам", "a_troll", "troll", "тролль", "хам", "нейрохам", "aut_troll", "auttroll", "аут_тролль", "ауттролль", "автотролль"]:\n'
        lines[i+1] = '                return\n'
        if lines[i+2].startswith('        if dot_cmd in'):
            lines[i+2] = '            if dot_cmd in ["only", "online", "онлайн", "вечный_онлайн", "вечныйонлайн", "always_online", "alwaysonline", "bot", "бот", "status", "статус"]:\n'
        print(f"Fixed lines around {i}")
        break

with open(r'C:\Users\user\Desktop\pomoshotru_bot\bot.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("Saved bot.py")
