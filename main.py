import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from parsers.telegram_parser import fetch_events_telegram
from parsers.eventbrite_parser import fetch_events_cyprus as fetch_eventbrite
from parsers.incyprus_parser import fetch_events_incyprus
from parsers.timeout_parser import fetch_events_timeout
from parsers.web_parser import fetch_events_web
from bot.poster import post_new_events, format_post
from bot.formatter_en import format_post_en
from db.categorizer import categorize
from db.city_extractor import extract_city

USE_FIREBASE = os.path.exists("data/serviceAccount.json") or bool(os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON"))
USE_THREADS = bool(os.environ.get("THREADS_ACCESS_TOKEN"))
USE_INSTAGRAM = bool(os.environ.get("INSTAGRAM_ACCESS_TOKEN"))
TG_CHANNEL_EN = os.environ.get("TELEGRAM_CHANNEL_EN", "")  # английский канал

if USE_FIREBASE:
    from db.firebase import save_events_batch, mark_posted, cleanup_old_events

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
    all_events += fetch_events_web()

    print(f"Всего событий собрано: {len(all_events)}")

    # Дедупликация — fuzzy match по заголовку (rapidfuzz, порог 88%)
    try:
        from rapidfuzz import fuzz
        unique_events = []
        seen_titles = []
        for event in all_events:
            title = (event.get("title") or "")[:80].lower().strip()
            if not title:
                continue
            is_dup = any(fuzz.token_sort_ratio(title, s) >= 88 for s in seen_titles)
            if not is_dup:
                seen_titles.append(title)
                unique_events.append(event)
        all_events = unique_events
    except ImportError:
        # rapidfuzz не установлен — простая дедупликация
        seen = set()
        all_events = [e for e in all_events if (k := (e.get("title") or "")[:50].lower().strip()) and not seen.add(k) and k not in seen]
    print(f"После дедупликации: {len(all_events)}")

    # Фильтр по дате — только актуальные события (не старше 60 дней, не в прошлом)
    from datetime import datetime, timedelta
    import re as _re
    now = datetime.now()
    cutoff_past = now - timedelta(days=3)   # разрешаем события до 3 дней назад
    cutoff_future = now + timedelta(days=90) # не дальше 90 дней вперёд

    def _parse_event_date(d: str):
        for fmt in ("%d %b %Y", "%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(d.strip(), fmt)
            except Exception:
                pass
        return None

    filtered = []
    for event in all_events:
        d = _parse_event_date(event.get("date", ""))
        source = event.get("source", "")
        if d is None:
            # RSS без читаемой даты — выбрасываем (старые архивные посты)
            # TG без даты — берём (у телеграм-постов часто нет даты события)
            if source == "tg":
                filtered.append(event)
        elif cutoff_past <= d <= cutoff_future:
            filtered.append(event)

    print(f"После фильтра по дате: {len(filtered)} (было {len(all_events)})")

    # Noise-фильтр применяем ко ВСЕМ источникам (включая TG и kiprinform)
    from parsers.web_parser import _quality_score, _is_event, NOISE_PHRASES
    def _is_noise_global(event: dict) -> bool:
        text = ((event.get("title") or "") + " " + (event.get("full_text") or "")).lower()
        return any(p in text for p in NOISE_PHRASES)

    all_events = [e for e in filtered if not _is_noise_global(e)]

    # Фильтр качества — только события с оценкой >= 1 (кроме TG без описания)
    all_events = [e for e in all_events if e.get("source") == "tg" or _quality_score(e) >= 1]
    print(f"После фильтра качества: {len(all_events)}")

    # Категоризация + извлечение города
    for event in all_events:
        event["category"] = categorize(event)
        if not event.get("city") or event.get("city") == "Cyprus":
            detected = extract_city((event.get("title") or "") + " " + (event.get("full_text") or ""))
            if detected:
                event["city"] = detected

    # Firebase — сначала сохраняем без перевода
    if USE_FIREBASE:
        cleanup_old_events(days=30)
        new_in_db = save_events_batch(all_events)
        print(f"[firebase] Новых в базе: {new_in_db}")

        from db.firebase import get_unposted
        events_to_post = get_unposted(platform="tg", limit=5)

        # Переводим только те что будем постить (5 штук максимум)
        from bot.translator import translate_to_english
        for event in events_to_post:
            if not event.get("title_en"):
                event["title_en"] = translate_to_english(event.get("title", ""))
            if not event.get("full_text_en"):
                src = event.get("full_text") or event.get("title") or ""
                event["full_text_en"] = translate_to_english(src[:500])
        print(f"[firebase] К публикации в TG: {len(events_to_post)}")
        print(f"[firebase] К публикации в TG: {len(events_to_post)}")
    else:
        print("[firebase] serviceAccount.json не найден — пропускаем БД")
        events_to_post = all_events

    # TG — русский канал
    post_new_events(events_to_post)

    # TG — английский канал (отдельный флаг posted_tg_en)
    if TG_CHANNEL_EN and TG_CHANNEL_EN != os.environ.get("TELEGRAM_CHANNEL_ID", "") and USE_FIREBASE:
        from db.firebase import get_unposted as _get_unposted_en
        events_to_post_en = _get_unposted_en(platform="tg_en", limit=5)
        print(f"[tg-en] Постим в {TG_CHANNEL_EN}: {len(events_to_post_en)}")
        post_new_events(events_to_post_en, channel_override=TG_CHANNEL_EN, formatter=format_post_en)

    # Threads — используем posted_threads из Firebase
    if USE_THREADS:
        print("[threads] Постим в Threads...")
        from db.firebase import get_unposted as _get_unposted_th, mark_posted as _mark_th
        from social.threads_poster import post_event_bilingual
        import time as _time
        threads_events = _get_unposted_th(platform="threads", limit=3) if USE_FIREBASE else all_events
        for event in threads_events:
            eid = event.get("id")
            ok = post_event_bilingual(event)
            if ok:
                print(f"[threads] Опубликовано: {event.get('title', '')[:50]}")
                if USE_FIREBASE:
                    try: _mark_th(eid, "threads")
                    except Exception: pass
                _time.sleep(15)

    # Instagram — тоже через Firebase
    if USE_INSTAGRAM:
        print("[instagram] Постим в Instagram...")
        from db.firebase import get_unposted as _get_unposted_ig, mark_posted as _mark_ig
        ig_events = _get_unposted_ig(platform="instagram", limit=10) if USE_FIREBASE else all_events
        new = post_events_to_instagram(ig_events, format_post_en, set())
        if USE_FIREBASE:
            for eid in new:
                try: _mark_ig(eid, "instagram")
                except Exception: pass

    print("=== Готово ===")


if __name__ == "__main__":
    main()
