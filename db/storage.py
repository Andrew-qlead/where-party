"""
Перезаливка картинок событий в Supabase Storage.

IG CDN-ссылки протухают через недели → в основном приложении (wrpt-app,
Supabase) карточки останутся без фото. Скачиваем картинку один раз и кладём
в публичный бакет 'event-images'; постоянный URL идёт и в Supabase (image_url),
и в Firebase (photo_url) — одна вечная ссылка на оба приложения.

ENV: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (те же, что для sync_supabase).
"""
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
BUCKET = "event-images"

_bucket_checked = False


def _ensure_bucket() -> None:
    """Создаёт публичный бакет, если его нет (идемпотентно)."""
    global _bucket_checked
    if _bucket_checked:
        return
    _bucket_checked = True
    try:
        import requests
        r = requests.post(
            f"{SUPABASE_URL}/storage/v1/bucket",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
            },
            json={"id": BUCKET, "name": BUCKET, "public": True},
            timeout=10,
        )
        # 200 — создан, 400/409 — уже существует
        if r.status_code not in (200, 400, 409):
            print(f"[storage] создание бакета: HTTP {r.status_code} {r.text[:120]}")
    except Exception as e:
        print(f"[storage] не смог проверить бакет: {str(e)[:80]}")


def _download(url: str):
    if not url or not url.startswith("http"):
        return None
    try:
        import requests
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and r.content:
            return r.content
    except Exception:
        pass
    return None


def _upload(external_id: str, data: bytes) -> str | None:
    """Заливает байты и возвращает публичный URL, или None при ошибке."""
    import requests
    path = f"{external_id}.jpg"
    try:
        r = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{path}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "image/jpeg",
                "x-upsert": "true",
            },
            data=data,
            timeout=15,
        )
        if r.status_code in (200, 201):
            return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"
        print(f"[storage] upload {path}: HTTP {r.status_code} {r.text[:120]}")
    except Exception as e:
        print(f"[storage] ошибка заливки {path}: {str(e)[:80]}")
    return None


def rehost_images(events: list[dict]) -> None:
    """Для каждого события с картинкой: заливает в Supabase Storage и
    заменяет photo_url на постоянный публичный URL. Мутирует events."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[storage] SUPABASE_URL/KEY не заданы — пропускаем перезаливку фото")
        return

    _ensure_bucket()
    rehosted = 0
    for event in events:
        data = event.pop("_image_bytes", None)  # переиспользуем байты из enrich
        if data is None:
            data = _download(event.get("photo_url", ""))
        if not data:
            continue
        public_url = _upload(event["id"], data)
        if public_url:
            event["photo_url"] = public_url
            rehosted += 1
    print(f"[storage] перезалито фото: {rehosted}")
