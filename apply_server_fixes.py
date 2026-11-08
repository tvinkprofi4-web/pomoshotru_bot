import os
import sys

# 1. Patch premium_client.py
pc_path = r"C:\Users\user\Desktop\pomoshotru_bot\premium_client.py"
with open(pc_path, "r", encoding="utf-8") as f:
    pc_content = f.read()

old_block = """                except Exception as loop_e:
                    if "AuthKeyDuplicatedError" in str(loop_e) or "session" in str(loop_e).lower():
                        logger.warning(f"Telethon session expired/duplicated: {loop_e}. Using Business connection.")
                        _is_ready = False
                        await asyncio.sleep(3600)"""

new_block = """                except Exception as loop_e:
                    if "AuthKeyDuplicatedError" in str(loop_e) or "session" in str(loop_e).lower():
                        logger.warning(f"Telethon session revoked/duplicated: {loop_e}. Disconnecting and disabling Userbot thread.")
                        try:
                            if _telethon_client:
                                await _telethon_client.disconnect()
                        except Exception:
                            pass
                        _is_ready = False
                        return"""

if old_block in pc_content:
    pc_content = pc_content.replace(old_block, new_block, 1)
    with open(pc_path, "w", encoding="utf-8") as f:
        f.write(pc_content)
    print("premium_client.py patched successfully!")
else:
    print("premium_client.py: target block already patched or not found")

# 2. Patch ai_roaster.py with comprehensive refusal filter
ar_path = r"C:\Users\user\Desktop\pomoshotru_bot\ai_roaster.py"
with open(ar_path, "r", encoding="utf-8") as f:
    ar_content = f.read()

refusal_def = '''
REFUSAL_TRIGGERS = [
    "не буду", "не могу", "не считаю", "как ии", "как искусственный", "как языковая",
    "языковой модел", "выйду из роли", "прямой отказ", "нарушает", "правила",
    "политик", "безопасност", "оскорб", "дискриминац", "этическ", "извините",
    "я всего лишь", "недопустимо", "неприемлемо", "не стану", "не поддерживаю",
    "морально", "токсичн", "уважительн", "деструктивн", "согласн", "поведения",
    "i cannot", "i can't", "i am sorry", "as an ai", "as a language model",
    "violates", "safety policy", "guidelines", "unethical", "offensive"
]

def is_ai_refusal(text: str) -> bool:
    if not text:
        return True
    low = text.lower()
    return any(t in low for t in REFUSAL_TRIGGERS)
'''

if "def is_ai_refusal" not in ar_content:
    ar_content = ar_content.replace("logger = logging.getLogger(__name__)", "logger = logging.getLogger(__name__)\n" + refusal_def, 1)

old_check = '''                            refusals = ["не буду", "не могу", "как ии", "как языковая", "выйду из роли", "прямой отказ"]
                            if any(r in cand_text.lower() for r in refusals):
                                continue
                            cleaned = clean_evil_response(cand_text)
                            if cleaned and len(cleaned) > 3:
                                roast_result = cleaned
                                break'''

new_check = '''                            if is_ai_refusal(cand_text):
                                logger.info(f"AI refusal intercepted and discarded from {model}: {cand_text[:40]}...")
                                continue
                            cleaned = clean_evil_response(cand_text)
                            if is_ai_refusal(cleaned):
                                logger.info(f"AI refusal intercepted in cleaned response from {model}")
                                continue
                            if cleaned and len(cleaned) > 3:
                                roast_result = cleaned
                                break'''

if old_check in ar_content:
    ar_content = ar_content.replace(old_check, new_check, 1)
    with open(ar_path, "w", encoding="utf-8") as f:
        f.write(ar_content)
    print("ai_roaster.py patched successfully!")
else:
    print("ai_roaster.py: check block already patched or not found")
