import time
import subprocess
import sys
import threading
import os
from dotenv import load_dotenv

load_dotenv()

INTERVAL_MINUTES = 30

def run_bot():
    print("[worker] Запускаю бот-сервер...", flush=True)
    subprocess.run([sys.executable, "bot/bot_server.py"])

def run_main():
    print("[worker] Запускаю парсинг...", flush=True)
    result = subprocess.run([sys.executable, "main.py"])
    print(f"[worker] Парсинг завершён, код {result.returncode}", flush=True)

if __name__ == "__main__":
    print(f"[worker] Стартую. Парсинг каждые {INTERVAL_MINUTES} мин.", flush=True)

    # Бот в отдельном потоке — работает всегда
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Парсинг сразу и потом по расписанию
    run_main()
    while True:
        time.sleep(INTERVAL_MINUTES * 60)
        run_main()
