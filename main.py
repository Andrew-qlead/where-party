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
from parsers.instagram_parser import fetch_events_instagram
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
    from datetime import datetime, timedelta, timezone
    print("=== Where Party Cyprus — запуск ===")
    all_events = []

    all_events += fetch_events_telegram()
    all_events += fetch_eventbrite()
    all_events += fetch_events_incyprus()
    all_events += fetch_events_timeout()
    all_events += fetch_events_web()
    all_events += fetch_events_instagram()

    print(f"Всего событий собрано: {len(all_events)}")

    # Дедупликация — fuzzy match по заголовку (rapidfuzz, порог 88%)
    # Также загружаем заголовки из Firebase (последние 7 дней) чтобы не дублировать
    # события которые уже были в прошлых циклах
    existing_titles = []
    if USE_FIREBASE:
        try:
            from db.firebase import get_db as _get_db
            _db = _get_db()
            _cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            _docs = _db.collection("events").where("created_at", ">=", _cutoff).stream()
            existing_titles = [
                (d.to_dict().get("title") or "")[:80].lower().strip()
                for d in _docs
            ]
            print(f"[dedup] Загружено {len(existing_titles)} заголовков из Firebase для кросс-цикловой дедупликации")
        except Exception as _ex:
            print(f"[dedup] Не удалось загрузить заголовки из Firebase: {_ex}")

    try:
        from rapidfuzz import fuzz
        unique_events = []
        seen_titles = list(existing_titles)  # стартуем с уже известными
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
        seen = set(existing_titles)
        all_events = [e for e in all_events if (k := (e.get("title") or "")[:50].lower().strip()) and k not in seen and not seen.add(k)]
    print(f"После дедупликации: {len(all_events)}")

    # Фильтр по дате — только актуальные события (не старше 60 дней, не в прошлом)
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
    from parsers.web_parser import _quality_score, NOISE_PHRASES
    from db.categorizer import categorize as _categorize_early
    import re as _re
    OLD_YEAR_RE = _re.compile(r'\b20(1[3-9]|2[0-5])\b')
    def _is_noise_global(event: dict) -> bool:
        title = event.get("title") or ""
        text = (title + " " + (event.get("full_text") or "")).lower()
        if any(p in text for p in NOISE_PHRASES):
            return True
        if OLD_YEAR_RE.search(title):
            return True
        return False

    all_events = [e for e in filtered if not _is_noise_global(e)]

    # Whitelist: для не-TG источников пропускаем только если событие
    # распознаётся как конкретная категория (не "other") И quality >= 1
    # TG-каналы доверяем полностью
    strict = []
    for e in all_events:
        cat = _categorize_early(e)
        if cat != "other":
            e["category"] = cat
            strict.append(e)
        else:
            print(f"[filter] Отброшено (not event): {e.get('title','')[:60]}")
    all_events = strict
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

        from db.firebase import get_unposted, update_translations
        from bot.translator import translate_to_english, translate_to_russian as _translate_ru

        # Берём больше чтобы после фильтра осталось 5
        events_to_post_all = get_unposted(platform="tg", limit=20)
        for event in events_to_post_all:
            # EN-перевод для мини-аппа
            if not event.get("title_en"):
                event["title_en"] = translate_to_english(event.get("title", ""))
            if not event.get("full_text_en"):
                src = event.get("full_text") or event.get("title") or ""
                event["full_text_en"] = translate_to_english(src[:500])
            # Сохраняем переводы обратно в Firebase (для мини-аппа)
            if event.get("title_en"):
                update_translations(event["id"], event["title_en"], event.get("full_text_en", ""))

            # Если full_text на английском — переводим на RU для отображения в RU-канале
            full_text = event.get("full_text") or ""
            cyrillic_ratio = sum(1 for c in full_text if 'Ѐ' <= c <= 'ӿ') / max(len(full_text), 1)
            if full_text and cyrillic_ratio < 0.15:
                ru_body = _translate_ru(full_text[:500])
                event["full_text"] = ru_body

        # RU канал — только события с кириллическим заголовком ИЛИ которые можно перевести
        # Включаем также EN-события у которых есть перевод заголовка на RU
        def _is_ru_ready(e: dict) -> bool:
            title = e.get("title", "")
            cyrillic = sum(1 for c in title if 'Ѐ' <= c <= 'ӿ')
            return cyrillic / max(len(title), 1) >= 0.15

        events_for_ru = [e for e in events_to_post_all if _is_ru_ready(e)][:5]
        events_skip_ru = [e for e in events_to_post_all if e not in events_for_ru]
        # Английские события помечаем как posted_tg чтобы не зависали в очереди
        for event in events_skip_ru:
            try: mark_posted(event["id"], "tg")
            except Exception: pass
        events_to_post = events_for_ru
        print(f"[firebase] К публикации в TG (RU): {len(events_to_post)}")
    else:
        print("[firebase] serviceAccount.json не найден — пропускаем БД")
        events_to_post = all_events

    # TG — русский канал
    post_new_events(events_to_post)

    # TG — английский канал (отдельный флаг posted_tg_en)
    if TG_CHANNEL_EN and TG_CHANNEL_EN != os.environ.get("TELEGRAM_CHANNEL_ID", "") and USE_FIREBASE:
        from db.firebase import get_unposted as _get_unposted_en, update_translations as _upd_tr
        from bot.translator import translate_to_english as _translate
        events_to_post_en = _get_unposted_en(platform="tg_en", limit=5)
        for event in events_to_post_en:
            if not event.get("title_en"):
                event["title_en"] = _translate(event.get("title", ""))
            if not event.get("full_text_en"):
                src = event.get("full_text") or event.get("title") or ""
                event["full_text_en"] = _translate(src[:500])
            if event.get("title_en"):
                _upd_tr(event["id"], event["title_en"], event.get("full_text_en", ""))
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

    # Мониторинг — запускаем в конце каждого цикла
    if USE_FIREBASE:
        try:
            from bot.monitor import run_health_check, send_daily_report
            from db.firebase import get_db
            db = get_db()
            run_health_check(db)
            # Ежедневный отчёт — раз в сутки (по часу в метке)
            if datetime.now().hour == 9:
                send_daily_report(db)
        except Exception as ex:
            print(f"[monitor] error: {ex}")

    print("=== Готово ===")


if __name__ == "__main__":
    main()
