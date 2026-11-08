import os
import sys
import time
import subprocess
import logging

LOG_FILE = os.path.join(os.path.dirname(__file__), "bot_watchdog.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

BOT_SCRIPT = os.path.join(os.path.dirname(__file__), "bot.py")

logging.info("=== Pomoshotru Watchdog starting... ===")

while True:
    try:
        logging.info("Starting bot.py process...")
        p = subprocess.Popen([sys.executable, BOT_SCRIPT], cwd=os.path.dirname(__file__))
        p.wait()
        logging.warning(f"bot.py exited with code {p.returncode}. Restarting in 5s...")
    except Exception as e:
        logging.error(f"Watchdog exception: {e}")
    time.sleep(5)
