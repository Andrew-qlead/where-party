"""
Показывает следующие 5 постов которые пойдут в @WrPtCy — без отправки.
Запуск: railway run --service pacific-forgiveness python3 scripts/preview_next_posts.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

from db.firebase import get_unposted
from bot.poster import format_post

events = get_unposted(platform="tg", limit=5)
print(f"Следующих постов: {len(events)}\n")
print("=" * 60)

for i, event in enumerate(events, 1):
    print(f"\n── ПОСТ {i} ──────────────────────────────────────")
    print(f"ID:     {event.get('id')}")
    print(f"Дата:   {event.get('date')}")
    print(f"Город:  {event.get('city')}")
    print(f"Фото:   {event.get('photo_url') or '—'}")
    print(f"URL:    {event.get('url') or '—'}")
    print()
    print(format_post(event))
    print()
