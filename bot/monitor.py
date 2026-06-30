"""
Модуль самодиагностики и автофикса.
Запускается в конце каждого цикла воркера.
"""
import os
import requests
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")  # личный chat_id для алертов


def _alert(msg: str):
    """Шлём алерт в личку администратору."""
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        print(f"[monitor] ALERT (no admin chat): {msg}")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_CHAT_ID, "text": f"⚠️ Where Party Monitor\n\n{msg}"},
            timeout=10,
        )
    except Exception as ex:
        print(f"[monitor] alert send error: {ex}")


def _has_cyrillic(text: str) -> bool:
    return sum(1 for c in (text or "") if "Ѐ" <= c <= "ӿ") > len(text or " ") * 0.15


def run_health_check(db) -> dict:
    """
    Проверяем состояние базы и каналов.
    Возвращаем словарь с результатами + выполняем автофиксы.
    """
    issues = []
    fixes = []
    now = datetime.now(timezone.utc)
    cutoff_stale = (now - timedelta(hours=3)).isoformat()

    try:
        events_col = db.collection("events")
        all_docs = list(events_col.limit(500).stream())
        total = len(all_docs)

        # 1. Считаем статусы постинга
        unposted_ru = 0
        unposted_en = 0
        missing_title_en = 0
        wrong_lang_in_ru_queue = []   # события без кириллицы в очереди RU
        stale_unposted = 0

        for doc in all_docs:
            d = doc.to_dict()
            created = d.get("created_at", "")

            if not d.get("posted_tg"):
                unposted_ru += 1
                # Зависшие > 3 часов без кириллицы → автофикс
                if not _has_cyrillic(d.get("title", "")) and created < cutoff_stale:
                    wrong_lang_in_ru_queue.append(doc.id)

            if not d.get("posted_tg_en"):
                unposted_en += 1

            if not d.get("title_en") and d.get("source", "") not in (
                "cyprus-mail-whatson", "cyprus-mail-entertainment", "cyprus-mail-kids",
                "visitcyprus", "parikiaki", "timeout", "incyprus", "eventbrite",
            ):
                missing_title_en += 1

            if created < cutoff_stale and not d.get("posted_tg") and not d.get("posted_tg_en"):
                stale_unposted += 1

        # 2. Автофикс: помечаем англ. события из очереди RU как posted_tg
        if wrong_lang_in_ru_queue:
            for eid in wrong_lang_in_ru_queue:
                try:
                    db.collection("events").document(eid).update({
                        "posted_tg": True,
                        "posted_tg_at": now.isoformat(),
                    })
                except Exception:
                    pass
            fixes.append(f"Помечено posted_tg для {len(wrong_lang_in_ru_queue)} англ. событий в RU-очереди")

        # 3. Автофикс: заполняем title_en для англ. источников у которых пустой
        en_sources = {"cyprus-mail-whatson", "cyprus-mail-entertainment", "cyprus-mail-kids",
                      "visitcyprus", "parikiaki", "timeout", "incyprus", "eventbrite"}
        fixed_en = 0
        for doc in all_docs:
            d = doc.to_dict()
            if d.get("source", "") in en_sources and not d.get("title_en") and d.get("title"):
                try:
                    db.collection("events").document(doc.id).update({
                        "title_en": d["title"],
                        "full_text_en": d.get("full_text", ""),
                    })
                    fixed_en += 1
                except Exception:
                    pass
        if fixed_en:
            fixes.append(f"Заполнено title_en для {fixed_en} событий из англ. источников")

        # 4. Определяем проблемы для алерта
        if unposted_ru > 80:
            issues.append(f"RU очередь застряла: {unposted_ru} событий не опубликовано")
        if unposted_en > 200:
            issues.append(f"EN очередь большая: {unposted_en} событий")
        if stale_unposted > 100:
            issues.append(f"Зависших >3ч событий: {stale_unposted}")

        result = {
            "total": total,
            "unposted_ru": unposted_ru,
            "unposted_en": unposted_en,
            "missing_title_en": missing_title_en,
            "issues": issues,
            "fixes": fixes,
        }

        print(f"[monitor] Всего: {total}, RU очередь: {unposted_ru}, EN очередь: {unposted_en}")
        if fixes:
            print(f"[monitor] Автофиксы: {'; '.join(fixes)}")
        if issues:
            msg = "\n".join(issues)
            if fixes:
                msg += "\n\nВыполнены автофиксы:\n" + "\n".join(fixes)
            _alert(msg)

        return result

    except Exception as ex:
        print(f"[monitor] health_check error: {ex}")
        return {}


def send_daily_report(db):
    """Отправляем ежедневный краткий отчёт в личку."""
    if not ADMIN_CHAT_ID:
        return
    try:
        all_docs = list(db.collection("events").limit(500).stream())
        total = len(all_docs)
        posted_ru = sum(1 for d in all_docs if d.to_dict().get("posted_tg"))
        posted_en = sum(1 for d in all_docs if d.to_dict().get("posted_tg_en"))
        with_title_en = sum(1 for d in all_docs if d.to_dict().get("title_en"))

        msg = (
            f"📊 Where Party — дневной отчёт\n"
            f"{'─'*25}\n"
            f"События в базе: {total}\n"
            f"Опубликовано RU: {posted_ru}\n"
            f"Опубликовано EN: {posted_en}\n"
            f"Имеют title_en: {with_title_en} из {total}\n"
            f"Очередь RU: {total - posted_ru}\n"
            f"Очередь EN: {total - posted_en}"
        )
        _alert(msg.replace("⚠️ Where Party Monitor\n\n", ""))
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_CHAT_ID, "text": msg},
            timeout=10,
        )
    except Exception as ex:
        print(f"[monitor] daily report error: {ex}")
