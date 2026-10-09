import sys
import os
import json
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from parsers.instagram_parser import fetch_events_instagram
from bot.poster import post_new_events, format_post
from bot.formatter_en import format_post_en
from db.categorizer import categorize
from db.city_extractor import extract_city, extract_city_from_source

USE_FIREBASE = os.path.exists("data/serviceAccount.json") or bool(os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON"))
USE_SUPABASE = bool(os.environ.get("SUPABASE_URL")) and bool(os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
USE_ENRICH = bool(os.environ.get("ANTHROPIC_API_KEY"))  # Haiku: даты/venue/город/цена/категория
USE_STORAGE = USE_SUPABASE  # перезаливка фото в Supabase Storage (те же креды)
USE_THREADS = bool(os.environ.get("THREADS_ACCESS_TOKEN"))
USE_INSTAGRAM = bool(os.environ.get("INSTAGRAM_ACCESS_TOKEN"))
TG_CHANNEL_EN = os.environ.get("TELEGRAM_CHANNEL_EN", "")  # английский канал

if USE_FIREBASE:
    from db.firebase import save_events_batch, mark_posted, cleanup_past_events

if USE_THREADS:
    from social.threads_poster import post_events_to_threads

if USE_INSTAGRAM:
    from social.instagram_poster import post_events_to_instagram


def _should_fetch_ig() -> bool:
    """True если пора скрейпить Instagram (прошло APIFY_IG_INTERVAL_HOURS с
    прошлого скрейпа). Метка в /tmp живёт между 15-мин прогонами воркера;
    после редеплоя сбрасывается (максимум один лишний скрейп)."""
    import time
    try:
        interval = float(os.environ.get("APIFY_IG_INTERVAL_HOURS", "3")) * 3600
    except ValueError:
        interval = 3 * 3600
    marker = "/tmp/wp_last_ig_fetch"
    try:
        last = float(open(marker).read().strip())
    except Exception:
        last = 0.0
    if time.time() - last >= interval:
        try:
            open(marker, "w").write(str(time.time()))
        except Exception:
            pass
        return True
    return False


def _load_seen_ids() -> set:
    """Локальный кэш уже обработанных id (бэкап к Firebase — на случай сбоя
    чтения из базы). Живёт в /tmp между 15-мин прогонами воркера."""
    try:
        return set(json.load(open("/tmp/wp_seen_ids.json")))
    except Exception:
        return set()


def _save_seen_ids(ids: set) -> None:
    try:
        # держим кэш ограниченным (последние ~5000 id)
        json.dump(sorted(ids)[-5000:], open("/tmp/wp_seen_ids.json", "w"))
    except Exception:
        pass


def main():
    from datetime import datetime, timedelta, timezone
    print("=== Where Party Cyprus — запуск ===")
    all_events = []

    # Единственный источник — Instagram (через Apify). Остальные парсеры удалены.
    # Скрейп дорогой ($1.50/1000 постов у Apify за КАЖДЫЙ прогон), поэтому тянем
    # редко (APIFY_IG_INTERVAL_HOURS, дефолт 3ч), а постинг в каналы идёт каждые
    # 15 мин из очереди Firebase независимо от скрейпа.
    if _should_fetch_ig():
        all_events += fetch_events_instagram()
    else:
        print("[ig] пропуск скрейпа (интервал не истёк) — постим из очереди Firebase")

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

    # ТОЧНЫЙ дедуп по id ДО обогащения — чтобы НЕ платить Haiku повторно за уже
    # обработанный пост (id детерминирован от shortCode). Двойная защита:
    # известные id из Firebase + локальный кэш /tmp.
    if all_events:
        known_ids = _load_seen_ids()
        if USE_FIREBASE:
            try:
                from db.firebase import get_existing_ids
                known_ids |= get_existing_ids()
            except Exception as _ie:
                print(f"[dedup-id] Firebase недоступен, только локальный кэш: {_ie}")
        before = len(all_events)
        all_events = [e for e in all_events if e.get("id") and e["id"] not in known_ids]
        skipped = before - len(all_events)
        if skipped:
            print(f"[dedup-id] отброшено уже известных по id (не обогащаем повторно): {skipped}")
        # запоминаем id этих новых событий в локальный кэш сразу
        _save_seen_ids(known_ids | {e["id"] for e in all_events})
        print(f"После ID-дедупа (к обогащению): {len(all_events)}")

    # Обогащение через Haiku (дата с флаера, venue, город, цена, категория) —
    # ДО фильтра по дате, чтобы фильтр работал по реальной дате события, а не поста.
    # Гоним только на новых (уже дедуплицированных) событиях.
    if USE_ENRICH:
        try:
            from db.enrich import enrich_events
            all_events = enrich_events(all_events)
        except Exception as _en_ex:
            print(f"[enrich] error: {_en_ex}")

    # Перезаливка фото в Supabase Storage → постоянный photo_url для обоих приложений
    if USE_STORAGE:
        try:
            from db.storage import rehost_images
            rehost_images(all_events)
        except Exception as _st_ex:
            print(f"[storage] error: {_st_ex}")

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
    from parsers.noise_filter import _quality_score, NOISE_PHRASES
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
        cat = e.get("category") or _categorize_early(e)  # категория от Haiku в приоритете
        if cat != "other":
            e["category"] = cat
            strict.append(e)
        else:
            print(f"[filter] Отброшено (not event): {e.get('title','')[:60]}")
    all_events = strict
    print(f"После фильтра качества: {len(all_events)}")

    # Категоризация + извлечение города (Haiku-категория в приоритете)
    for event in all_events:
        event["category"] = event.get("category") or categorize(event)
        if not event.get("city") or event.get("city") == "Cyprus":
            detected = extract_city((event.get("title") or "") + " " + (event.get("full_text") or ""))
            if not detected:
                detected = extract_city_from_source(event.get("source", ""))
            if detected:
                event["city"] = detected

    # Supabase sync — уже после дедупа/фильтрации, до постинга
    if USE_SUPABASE:
        try:
            from sync_supabase import sync_to_supabase, cleanup_past_supabase
            cleanup_past_supabase(days_grace=1)  # прошедшие события + их фото из Storage
            sync_to_supabase(all_events)
        except Exception as _sync_ex:
            print(f"[supabase] sync error: {_sync_ex}")

    # Firebase — сначала сохраняем без перевода
    if USE_FIREBASE:
        cleanup_past_events(days_grace=1)  # удаляем прошедшие по ДАТЕ СОБЫТИЯ
        new_in_db = save_events_batch(all_events)
        print(f"[firebase] Новых в базе: {new_in_db}")

        from db.firebase import get_unposted, update_translations
        from bot.translator import translate_to_english, translate_to_russian as _translate_ru

        # Берём больше чтобы после фильтра осталось 5
        events_to_post_all = get_unposted(platform="tg", limit=20)
        def _is_en(s: str) -> bool:
            return bool(s) and sum(1 for c in s if 'Ѐ' <= c <= 'ӿ') / max(len(s), 1) < 0.15

        for event in events_to_post_all:
            # EN для мини-аппа: чистый EN от Haiku (title/desc_en), иначе перевод.
            # title из Firebase — это уже чистый англ-заголовок от Haiku.
            if not event.get("title_en"):
                event["title_en"] = event.get("title") or translate_to_english(event.get("title_ru", ""))
            if not event.get("full_text_en"):
                event["full_text_en"] = event.get("desc_en") or translate_to_english(
                    (event.get("full_text") or event.get("title") or "")[:500])
            if event.get("title_en"):
                update_translations(event["id"], event["title_en"], event.get("full_text_en", ""))

            # RU-канал: русский от Haiku (title_ru/desc_ru), иначе машинный фолбэк.
            # (title_en выше уже зафиксирован — перезапись title на русский на него не влияет.)
            if event.get("title_ru"):
                event["title"] = event["title_ru"]
            elif _is_en(event.get("title")):
                ru = _translate_ru(event["title"])
                if ru:
                    event["title"] = ru
            if event.get("desc_ru"):
                event["full_text"] = event["desc_ru"]
            elif _is_en(event.get("full_text")):
                ru = _translate_ru(event["full_text"][:500])
                if ru:
                    event["full_text"] = ru

        # RU-канал: постим ВСЕ события (заголовок и текст переведены на русский выше).
        # Раньше тут стоял фильтр _is_ru_ready — он выкидывал англоязычные IG-события,
        # и RU-канал оставался пустым. Убран: теперь дублируем всё в RU на русском.
        events_to_post = events_to_post_all[:5]
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
            # чистый EN от Haiku (title / desc_en), иначе перевод
            if not event.get("title_en"):
                event["title_en"] = event.get("title") or _translate(event.get("title_ru", ""))
            if not event.get("full_text_en"):
                event["full_text_en"] = event.get("desc_en") or _translate(
                    (event.get("full_text") or event.get("title") or "")[:500])
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
