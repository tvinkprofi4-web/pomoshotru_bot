import sys
import os
import asyncio
import qrcode
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import config

API_ID = int(config.TELEGRAM_API_ID)
API_HASH = str(config.TELEGRAM_API_HASH)

def save_session_to_config(new_session_str):
    cfg_path = os.path.join(os.path.dirname(__file__), "config.py")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg_content = f.read()

    import re
    cfg_content = re.sub(
        r'_CREATOR_DEFAULT_SESSION_STRING\s*=\s*".*?"',
        f'_CREATOR_DEFAULT_SESSION_STRING = "{new_session_str}"',
        cfg_content
    )

    with open(cfg_path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(cfg_content)

def generate_password_variants(pwd: str):
    variants = [pwd]

    lat_to_cyr = {
        'T': 'Т', 't': 'т',
        'e': 'е', 'E': 'Е',
        'a': 'а', 'A': 'А',
        'k': 'к', 'K': 'К',
        'o': 'о', 'O': 'О',
        'p': 'р', 'P': 'Р',
        'c': 'с', 'C': 'С',
        'x': 'х', 'X': 'Х',
        'y': 'у', 'Y': 'У',
        'B': 'В', 'M': 'М', 'H': 'Н'
    }
    cyr_to_lat = {v: k for k, v in lat_to_cyr.items()}

    # 1. Lowercase / Uppercase
    if pwd.lower() not in variants:
        variants.append(pwd.lower())
    if pwd.capitalize() not in variants:
        variants.append(pwd.capitalize())

    # 2. Cyrillic homoglyphs
    cyr_ver = "".join(lat_to_cyr.get(c, c) for c in pwd)
    if cyr_ver not in variants:
        variants.append(cyr_ver)
    if cyr_ver.lower() not in variants:
        variants.append(cyr_ver.lower())

    # 3. Latin from Cyrillic
    lat_ver = "".join(cyr_to_lat.get(c, c) for c in pwd)
    if lat_ver not in variants:
        variants.append(lat_ver)
    if lat_ver.lower() not in variants:
        variants.append(lat_ver.lower())

    # 4. Keyboard layout translations
    en_keys = "qwertyuiop[]asdfghjkl;'zxcvbnm,./QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?"
    ru_keys = "йцукенгшщзхъфывапролджэячсмитьбю.ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,"
    en_to_ru = dict(zip(en_keys, ru_keys))
    ru_to_en = dict(zip(ru_keys, en_keys))

    trans_ru = "".join(en_to_ru.get(c, c) for c in pwd)
    if trans_ru not in variants:
        variants.append(trans_ru)
    trans_en = "".join(ru_to_en.get(c, c) for c in pwd)
    if trans_en not in variants:
        variants.append(trans_en)

    return variants

async def qr_login_flow():
    print("=" * 60)
    print("      ВХОД ЧЕРЕЗ QR-КОД (БЕЗ СМС И БЕЗ КАПЧИ)")
    print("=" * 60)
    print("\nПодключение к Telegram...")

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    qr = await client.qr_login()

    # Generate QR Code image file
    qr_img_path = os.path.join(os.path.dirname(__file__), "login_qr.png")
    qr_builder = qrcode.QRCode(box_size=10, border=2)
    qr_builder.add_data(qr.url)
    qr_builder.make(fit=True)
    img = qr_builder.make_image(fill_color="black", back_color="white")
    img.save(qr_img_path)

    print("\n" + "=" * 60)
    print(" ИНСТРУКЦИЯ:")
    print(" 1. В Telegram на телефоне открой:")
    print("    Настройки -> Устройства -> Подключить устройство")
    print(" 2. Наведи камеру телефона на открывшийся QR-код на экране!")
    print("=" * 60 + "\n")

    # Automatically open the QR image on Windows screen
    try:
        if os.name == 'nt' and hasattr(os, 'startfile'):
            os.startfile(qr_img_path)
            print(" [OK] Картинка с QR-кодом открыта на твоём экране!")
    except Exception as e:
        print(f" (Файл с QR-кодом сохранен: {qr_img_path})")

    # Also display ASCII QR in terminal
    try:
        qr_console = qrcode.QRCode(border=1)
        qr_console.add_data(qr.url)
        qr_console.make(fit=True)
        print("\nИли отсканируй прямо из консоли:\n")
        qr_console.print_ascii(invert=True)
    except Exception:
        pass

    print("\nОжидание сканирования QR-кода с телефона (2 минуты)...")

    user = None
    try:
        user = await qr.wait(timeout=120)
    except SessionPasswordNeededError:
        print("\n" + "=" * 60)
        print(" У ВАС ВКЛЮЧЕН ОБЛАЧНЫЙ ПАРОЛЬ (2FA)!")
        print("=" * 60)

        # Show Telegram's official hint if available
        try:
            pwd_info = await client(functions.account.GetPasswordRequest())
            if pwd_info.hint:
                print(f"\n💡 ПОДСКАЗКА К ПАРОЛЮ ИЗ TELEGRAM: «{pwd_info.hint}»")
            else:
                print("\n💡 Подсказка к паролю в Telegram не установлена.")

            if getattr(pwd_info, "has_recovery", False):
                print("📧 К вашему аккаунту привязана почта восстановления пароля.")
        except Exception:
            pass

        print("\nЕсли вы уверены в пароле, просто введите его.")
        print("Скрипт автоматически проверит раскладки и похожие буквы (рус/англ).")

        while True:
            pwd = input("\nВведите пароль двухфакторной аутентификации (2FA): ").strip()
            if not pwd:
                print("Пароль не может быть пустым.")
                continue

            variants = generate_password_variants(pwd)
            success = False

            for v in variants:
                try:
                    if v != pwd:
                        print(f" -> Проверяем вариант раскладки/регистра: '{v}'...")
                    user = await client.sign_in(password=v)
                    print(f"\n[OK] ПАРОЛЬ ПОДОШЕЛ! (Использован вариант: '{v}')")
                    success = True
                    break
                except Exception as pe:
                    err_msg = str(pe)
                    if "invalid" in err_msg.lower() or "password" in err_msg.lower():
                        continue
                    else:
                        print(f" Ошибка Telegram: {pe}")
                        break

            if success:
                break
            else:
                print("\n[!] Ошибка: Telegram сервер отклонил введенный пароль и все его раскладки.")
                print("Как проверить или решить на телефоне прямо сейчас:")
                print("  1. Откройте в Telegram: Настройки -> Конфиденциальность -> Облачный пароль")
                print("  2. Попробуйте нажать 'Изменить пароль' и ввести его там (вы увидите, принимает ли его Telegram)")
                print("  3. Либо нажмите 'Отключить пароль' (или 'Забыли пароль?'), войдите через QR без пароля, а затем снова включите 2FA.")
                print("Попробуйте ввести пароль еще раз:")
    except Exception as e:
        print(f"\n Ошибка ожидания QR: {e}")
        input("\nНажмите Enter для выхода...")
        await client.disconnect()
        return

    new_session_str = client.session.save()
    me = await client.get_me()
    print("\n" + "=" * 60)
    print(" АВТОРИЗАЦИЯ УСПЕШНА!")
    print(f" Аккаунт: {me.first_name} (@{me.username})")
    print(f" ID: {me.id} | Premium: {getattr(me, 'premium', False)}")
    print("=" * 60)

    save_session_to_config(new_session_str)
    print("\n[OK] config.py успешно обновлен новой сессией!")

    if os.path.exists(qr_img_path):
        try:
            os.remove(qr_img_path)
        except Exception:
            pass

    await client.disconnect()
    print("\nГОТОВО! Нажмите Enter, чтобы закрыть окно, и напишите мне в чат...")
    input()

if __name__ == "__main__":
    asyncio.run(qr_login_flow())
