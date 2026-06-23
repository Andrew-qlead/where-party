import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
API = f"https://api.telegram.org/bot{TOKEN}"
MINIAPP_URL = "https://andrew-qlead.github.io/where-party/"

WELCOME_RU = "🗓 Все события Кипра в одном месте — концерты, вечеринки, выставки, спорт."
WELCOME_EN = "🗓 All Cyprus events in one place — concerts, parties, art, sport and more."

def send_welcome(chat_id: int):
    requests.post(f"{API}/sendMessage", json={
        "chat_id": chat_id,
        "text": WELCOME_RU,
        "reply_markup": {
            "inline_keyboard": [[{
                "text": "📅 Открыть афишу",
                "web_app": {"url": MINIAPP_URL}
            }]]
        }
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
