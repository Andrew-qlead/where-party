import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from parsers.telegram_parser import fetch_events_telegram
from parsers.eventbrite_parser import fetch_events_cyprus as fetch_eventbrite
from parsers.incyprus_parser import fetch_events_incyprus
from parsers.timeout_parser import fetch_events_timeout
from bot.poster import post_new_events, format_post
from bot.formatter_en import format_post_en
from db.categorizer import categorize

USE_FIREBASE = os.path.exists("data/serviceAccount.json") or bool(os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON"))
USE_THREADS = bool(os.environ.get("THREADS_ACCESS_TOKEN"))
USE_INSTAGRAM = bool(os.environ.get("INSTAGRAM_ACCESS_TOKEN"))
TG_CHANNEL_EN = os.environ.get("TELEGRAM_CHANNEL_EN", "")  # английский канал

if USE_FIREBASE:
    from db.firebase import save_events_batch, mark_posted

if USE_THREADS:
    from social.threads_poster import post_events_to_threads

if USE_INSTAGRAM:
    from social.instagram_poster import post_events_to_instagram


def main():
    print("=== Where Party Cyprus — запуск ===")
    all_events = []

    all_events += fetch_events_telegram()
    all_events += fetch_eventbrite()
    all_events += fetch_events_incyprus()
    all_events += fetch_events_timeout()

    print(f"Всего событий собрано: {len(all_events)}")

    # Дедупликация по заголовку
    seen_titles = set()
    unique_events = []
    for event in all_events:
        title_key = (event.get("title") or "")[:50].lower().strip()
        if title_key and title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_events.append(event)
    all_events = unique_events
    print(f"После дедупликации: {len(all_events)}")

    # Категоризация
    for event in all_events:
        event["category"] = categorize(event)

    # Перевод на английский (title_en, full_text_en)
    from bot.translator import translate_to_english
    for event in all_events:
        if not event.get("title_en"):
            event["title_en"] = translate_to_english(event.get("title", ""))
        if not event.get("full_text_en"):
            src = event.get("full_text") or event.get("title") or ""
            event["full_text_en"] = translate_to_english(src[:1000])

    # Firebase
    if USE_FIREBASE:
        new_in_db = save_events_batch(all_events)
        print(f"[firebase] Новых в базе: {new_in_db}")
    else:
        print("[firebase] serviceAccount.json не найден — пропускаем БД")

    # TG — русский канал
    post_new_events(all_events)

    # TG — английский канал (если задан)
    if TG_CHANNEL_EN:
        print(f"[tg-en] Постим в английский канал {TG_CHANNEL_EN}")
        post_new_events(all_events, channel_override=TG_CHANNEL_EN, formatter=format_post_en)

    # Threads — двуязычный постинг
    if USE_THREADS:
        print("[threads] Постим в Threads...")
        from bot.poster import load_posted_ids, save_posted_ids
        from social.threads_poster import post_event_bilingual
        posted = load_posted_ids("data/posted_threads.json")
        new_posted = set()
        for event in all_events:
            eid = event.get("id")
            if eid in posted:
                continue
            ok = post_event_bilingual(event)
            if ok:
                new_posted.add(eid)
                print(f"[threads] Опубликовано: {event.get('title', '')[:50]}")
                import time; time.sleep(15)
        save_posted_ids(posted | new_posted, "data/posted_threads.json")

    # Instagram
    if USE_INSTAGRAM:
        print("[instagram] Постим в Instagram...")
        from bot.poster import load_posted_ids, save_posted_ids
        posted = load_posted_ids("data/posted_instagram.json")
        new = post_events_to_instagram(all_events, format_post_en, posted)
        save_posted_ids(posted | new, "data/posted_instagram.json")

    print("=== Готово ===")


if __name__ == "__main__":
    main()
