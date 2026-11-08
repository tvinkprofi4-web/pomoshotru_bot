# -*- coding: utf-8 -*-
import os
import sys
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
import qrcode
import config

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

API_ID = config.TELEGRAM_API_ID or 6
API_HASH = config.TELEGRAM_API_HASH or "eb06d4abfb49dc3eeb1aeb98ae0f581e"

async def main():
    print("=" * 60)
    print("⭐️ TELEGRAM PREMIUM USERBOT: ВХОД ПО QR-КОДУ")
    print("=" * 60)
    
    client = TelegramClient(
        StringSession(),
        API_ID,
        API_HASH,
        device_model="Desktop PC",
        system_version="Windows 11",
        app_version="5.5.5",
        lang_code="ru"
    )
    
    await client.connect()
    
    if not await client.is_user_authorized():
        print("📲 Генерирую QR-код для входа (без СМС и капчи)...")
        qr_login = await client.qr_login()
        
        qr = qrcode.QRCode(border=2)
        qr.add_data(qr_login.url)
        
        print("\n" + "—" * 60)
        print("📌 ИНСТРУКЦИЯ:")
        print("1. Открой Telegram на телефоне")
        print("2. Зайди в Настройки -> Устройства -> Подключить устройство (Link Device)")
        print("3. Наведи камеру на QR-код ниже:")
        print("—" * 60 + "\n")
        
        qr.print_ascii(invert=True)
        
        print(f"\n🔗 Или перейди по прямой ссылке: {qr_login.url}\n")
        print("⏳ Ожидаю сканирования QR-кода...")
        
        try:
            await qr_login.wait()
        except SessionPasswordNeededError:
            print("\n🔐 На аккаунте включен 2FA (Облачный пароль).")
            pwd = input("Введи свой 2FA пароль: ")
            await client.sign_in(password=pwd)
        except Exception as e:
            print(f"Ошибка ожидания QR: {e}")
            return
            
    me = await client.get_me()
    session_str = client.session.save()
    
    name = (me.first_name or "") + (" " + (me.last_name or "") if me.last_name else "")
    username = f"@{me.username}" if me.username else f"ID {me.id}"
    is_premium = getattr(me, "premium", False)
    
    print("\n" + "=" * 60)
    print("✅ АВТОРИЗАЦИЯ УСПЕШНО ПРОЙДЕНА!")
    print(f"👤 Аккаунт: {name} ({username})")
    print(f"⭐️ Telegram Premium: {'ДА (Активен)' if is_premium else 'НЕТ'}")
    print("=" * 60)
    
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    env_content = ""
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            env_content = f.read()
        
    if "TELEGRAM_SESSION_STRING=" in env_content:
        import re
        env_content = re.sub(r"TELEGRAM_SESSION_STRING=.*", f"TELEGRAM_SESSION_STRING={session_str}", env_content)
    else:
        env_content += f"\nTELEGRAM_API_ID={API_ID}\nTELEGRAM_API_HASH={API_HASH}\nTELEGRAM_SESSION_STRING={session_str}\n"
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content.strip() + "\n")
        
    print("💾 Сессия сохранена в .env файл!")
    print("🚀 Теперь бот может отправлять любые Premium-стикеры, эмодзи и реакции!")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
