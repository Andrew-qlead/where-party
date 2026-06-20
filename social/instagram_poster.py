import os
import requests
import time

# Instagram Graph API — нужен Instagram Business/Creator аккаунт
# связанный с Facebook Page + Facebook App с правами instagram_content_publish

INSTAGRAM_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID = os.environ.get("INSTAGRAM_USER_ID", "")

BASE_URL = "https://graph.facebook.com/v19.0"


def create_image_container(image_url: str, caption: str) -> str | None:
    """Создаём медиа-контейнер для фото."""
    url = f"{BASE_URL}/{INSTAGRAM_USER_ID}/media"
    r = requests.post(url, params={
        "image_url": image_url,
        "caption": caption[:2200],  # Instagram лимит
        "access_token": INSTAGRAM_TOKEN,
    }, timeout=15)
    if r.ok:
        return r.json().get("id")
    print(f"[instagram] create error: {r.text}")
    return None


def create_reel_container(video_url: str, caption: str) -> str | None:
    url = f"{BASE_URL}/{INSTAGRAM_USER_ID}/media"
    r = requests.post(url, params={
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption[:2200],
        "access_token": INSTAGRAM_TOKEN,
    }, timeout=15)
    if r.ok:
        return r.json().get("id")
    print(f"[instagram] reel error: {r.text}")
    return None


def wait_for_ready(container_id: str, max_wait: int = 60) -> bool:
    """Ждём пока Instagram обработает медиа."""
    url = f"{BASE_URL}/{container_id}"
    for _ in range(max_wait // 5):
        r = requests.get(url, params={
            "fields": "status_code",
            "access_token": INSTAGRAM_TOKEN,
        }, timeout=10)
        if r.ok and r.json().get("status_code") == "FINISHED":
            return True
        time.sleep(5)
    return False


def publish_container(container_id: str) -> bool:
    url = f"{BASE_URL}/{INSTAGRAM_USER_ID}/media_publish"
    r = requests.post(url, params={
        "creation_id": container_id,
        "access_token": INSTAGRAM_TOKEN,
    }, timeout=15)
    if not r.ok:
        print(f"[instagram] publish error: {r.text}")
    return r.ok


def post_to_instagram(caption: str, image_url: str) -> bool:
    if not INSTAGRAM_TOKEN or not INSTAGRAM_USER_ID:
        print("[instagram] токены не заданы")
        return False
    if not image_url:
        print("[instagram] фото обязательно для Instagram")
        return False

    container_id = create_image_container(image_url, caption)
    if not container_id:
        return False

    if not wait_for_ready(container_id):
        print("[instagram] медиа не готово")
        return False

    return publish_container(container_id)


def post_events_to_instagram(events: list[dict], formatter, posted_ids: set) -> set:
    """Постим события с фото в Instagram."""
    new_posted = set()
    for event in events:
        eid = event.get("id")
        if eid in posted_ids:
            continue
        image_url = event.get("image_url") or event.get("photo_url")
        if not image_url:
            continue  # Instagram требует фото
        caption = formatter(event)
        ok = post_to_instagram(caption, image_url)
        if ok:
            new_posted.add(eid)
            print(f"[instagram] Опубликовано: {event.get('title', eid)[:50]}")
            time.sleep(15)
        else:
            print(f"[instagram] Ошибка: {event.get('title', eid)[:50]}")
    return new_posted
