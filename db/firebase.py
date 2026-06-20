import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone

_db = None

def get_db():
    global _db
    if _db:
        return _db

    if not firebase_admin._apps:
        sa_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "data/serviceAccount.json")
        if not os.path.exists(sa_path):
            raise FileNotFoundError(
                f"Firebase serviceAccount.json не найден: {sa_path}\n"
                "Скачай его из Firebase Console → Project Settings → Service Accounts"
            )
        cred = credentials.Certificate(sa_path)
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    return _db


def save_event(event: dict) -> bool:
    """Сохраняем событие в Firestore. Возвращает True если новое, False если уже было."""
    try:
        db = get_db()
        event_id = event.get("id")
        if not event_id:
            return False

        ref = db.collection("events").document(event_id)
        doc = ref.get()

        if doc.exists:
            return False  # уже есть

        ref.set({
            **event,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "posted_tg": False,
            "posted_threads": False,
            "posted_instagram": False,
        })
        return True

    except Exception as ex:
        print(f"[firebase] Ошибка сохранения {event.get('id')}: {ex}")
        return False


def save_events_batch(events: list[dict]) -> int:
    """Сохраняем список событий, возвращает кол-во новых."""
    db = get_db()
    new_count = 0
    batch = db.batch()
    batch_size = 0

    for event in events:
        event_id = event.get("id")
        if not event_id:
            continue

        ref = db.collection("events").document(event_id)
        doc = ref.get()
        if doc.exists:
            continue

        batch.set(ref, {
            **event,
            "photo_path": None,  # не храним локальные пути
            "created_at": datetime.now(timezone.utc).isoformat(),
            "posted_tg": False,
            "posted_threads": False,
            "posted_instagram": False,
        })
        new_count += 1
        batch_size += 1

        # Firestore batch limit — 500 операций
        if batch_size >= 400:
            batch.commit()
            batch = db.batch()
            batch_size = 0

    if batch_size > 0:
        batch.commit()

    return new_count


def mark_posted(event_id: str, platform: str):
    """Отмечаем что событие опубликовано на платформе (tg / threads / instagram)."""
    try:
        db = get_db()
        db.collection("events").document(event_id).update({
            f"posted_{platform}": True,
            f"posted_{platform}_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as ex:
        print(f"[firebase] mark_posted error: {ex}")


def get_unposted(platform: str = "tg", limit: int = 50) -> list[dict]:
    """Получаем события которые ещё не запостили на платформу."""
    try:
        db = get_db()
        docs = (
            db.collection("events")
            .where(f"posted_{platform}", "==", False)
            .order_by("created_at")
            .limit(limit)
            .stream()
        )
        return [{"id": d.id, **d.to_dict()} for d in docs]
    except Exception as ex:
        print(f"[firebase] get_unposted error: {ex}")
        return []


def get_events_by_category(category: str, limit: int = 20) -> list[dict]:
    """Для Mini App — события по категории."""
    try:
        db = get_db()
        docs = (
            db.collection("events")
            .where("category", "==", category)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [{"id": d.id, **d.to_dict()} for d in docs]
    except Exception as ex:
        print(f"[firebase] get_events_by_category error: {ex}")
        return []
