import os
import requests
import time

# Threads API (Meta) — нужен Instagram Business аккаунт + Facebook App
# Документация: https://developers.facebook.com/docs/threads

THREADS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "")
THREADS_USER_ID = os.environ.get("THREADS_USER_ID", "")

BASE_URL = "https://graph.threads.net/v1.0"


def create_text_post(text: str) -> str | None:
    """Создаём контейнер поста, возвращает creation_id."""
    url = f"{BASE_URL}/{THREADS_USER_ID}/threads"
    r = requests.post(url, params={
        "media_type": "TEXT",
        "text": text[:500],  # Threads лимит
        "access_token": THREADS_TOKEN,
    }, timeout=15)
    if r.ok:
        return r.json().get("id")
    print(f"[threads] create error: {r.text}")
    return None


def create_photo_post(text: str, image_url: str) -> str | None:
    """Создаём контейнер с фото."""
    url = f"{BASE_URL}/{THREADS_USER_ID}/threads"
    r = requests.post(url, params={
        "media_type": "IMAGE",
        "image_url": image_url,
        "text": text[:500],
        "access_token": THREADS_TOKEN,
    }, timeout=15)
    if r.ok:
        return r.json().get("id")
    print(f"[threads] create photo error: {r.text}")
    return None


def publish_post(creation_id: str) -> bool:
    """Публикуем созданный контейнер."""
    url = f"{BASE_URL}/{THREADS_USER_ID}/threads_publish"
    r = requests.post(url, params={
        "creation_id": creation_id,
        "access_token": THREADS_TOKEN,
    }, timeout=15)
    if not r.ok:
        print(f"[threads] publish error: {r.text}")
    return r.ok


def post_to_threads(text: str, image_url: str = None) -> bool:
    if not THREADS_TOKEN or not THREADS_USER_ID:
        print("[threads] THREADS_ACCESS_TOKEN или THREADS_USER_ID не заданы")
        return False

    creation_id = create_photo_post(text, image_url) if image_url else create_text_post(text)
    if not creation_id:
        return False

    time.sleep(5)  # Threads требует паузу перед публикацией
    return publish_post(creation_id)


def post_events_to_threads(events: list[dict], formatter, posted_ids: set) -> set:
    """Постим новые события в Threads."""
    new_posted = set()
    for event in events:
        eid = event.get("id")
        if eid in posted_ids:
            continue
        text = formatter(event)
        ok = post_to_threads(text)
        if ok:
            new_posted.add(eid)
            print(f"[threads] Опубликовано: {event.get('title', eid)[:50]}")
            time.sleep(10)  # пауза между постами
        else:
            print(f"[threads] Ошибка: {event.get('title', eid)[:50]}")
    return new_posted
