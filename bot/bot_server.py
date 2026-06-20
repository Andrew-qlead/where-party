import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
API = f"https://api.telegram.org/bot{TOKEN}"

WELCOME_RU = (
    "👇 Нажми кнопку «тык» внизу экрана ↓\n"
    "Там вся афиша Кипра — вечеринки, концерты, выставки и многое другое."
)
WELCOME_EN = (
    "👇 Tap the «тык» button at the bottom of the screen ↓\n"
    "Find all Cyprus events — parties, concerts, exhibitions and more."
)

def send_welcome(chat_id: int):
    requests.post(f"{API}/sendMessage", json={
        "chat_id": chat_id,
        "text": WELCOME_RU,
    })

def get_updates(offset: int = 0):
    resp = requests.get(f"{API}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
    return resp.json().get("result", [])

def run():
    print("[bot] Запущен, жду /start...")
    offset = 0
    while True:
        try:
            updates = get_updates(offset)
            for upd in updates:
                offset = upd["update_id"] + 1
                msg = upd.get("message", {})
                text = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id")
                if chat_id and text.startswith("/start"):
                    send_welcome(chat_id)
                    print(f"[bot] Welcome sent to {chat_id}")
        except Exception as e:
            print(f"[bot] Ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run()
