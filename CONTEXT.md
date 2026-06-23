# WR PT — Where Party Cyprus · Контекст проекта

## Суть проекта
Агрегатор событий Кипра. Парсер собирает события → Firebase → Telegram каналы (RU+EN) + Мини-апп + Threads.

---

## Стек

| Компонент | Технология |
|---|---|
| Бэкенд / парсер | Python 3.12, Railway (worker.py, каждые 15 мин) |
| База данных | Firebase Firestore (проект: `whereparty-88938`) |
| Мини-апп | HTML/JS, GitHub Pages: `andrew-qlead.github.io/where-party/` |
| TG-бот | python-telegram-bot, long polling |
| Хостинг | Railway, сервис `pacific-forgiveness`, проект `pacific-forgiveness` |
| Социальные сети | Threads (`@iseealleye`), TG каналы |
| Переводы | deep-translator (Google Translate, без ключа) |

---

## Деплой

Railway **не подключён к GitHub автодеплою** — деплоить вручную:
```bash
cd /Users/illaviktorovna/where-party
railway up --service pacific-forgiveness --detach
```

Логи смотреть:
```bash
railway logs
```

Предпросмотр следующих постов (без отправки):
```bash
railway run --service pacific-forgiveness python3 scripts/preview_next_posts.py
```

Пометить все события как опубликованные (сброс):
```bash
railway run --service pacific-forgiveness python3 scripts/mark_all_posted_rest.py
```

---

## Структура файлов

```
/Users/illaviktorovna/where-party/
├── main.py                    # парсинг → фильтр → Firebase → посты
├── worker.py                  # Railway: бот-поток + main.py каждые 15 мин
├── requirements.txt
├── railway.json               # start: python worker.py
│
├── parsers/
│   ├── telegram_parser.py     # Telethon, 14 каналов (3 отключены — нет username)
│   ├── web_parser.py          # RSS источники + фильтр качества
│   ├── eventbrite_parser.py   # отключён (нет токена)
│   ├── incyprus_parser.py
│   └── timeout_parser.py
│
├── db/
│   ├── firebase.py            # get_db, save_events_batch, mark_posted, get_unposted
│   ├── categorizer.py         # категоризация по ключевым словам
│   └── city_extractor.py      # извлечение города из текста
│
├── bot/
│   ├── bot_server.py          # long-poll бот, /start → мини-апп
│   ├── poster.py              # post_new_events, format_post, фото через multipart
│   ├── formatter_en.py        # EN форматтер для @partycy
│   └── translator.py          # translate_to_english() через deep-translator
│
├── social/
│   └── threads_poster.py      # один EN пост на событие
│
├── miniapp/
│   ├── index.html             # мини-апп (карточки, фильтры, избранное, шара)
│   ├── landing.html           # SEO лендинг
│   ├── submit.html            # форма добавления события
│   ├── admin.html             # веб-админка (пароль: wrpt2024admin)
│   └── firebase-config.js
│
└── scripts/
    ├── preview_next_posts.py      # предпросмотр следующих 5 постов
    ├── mark_all_posted_rest.py    # сброс флагов (REST API, работает на Python 3.14)
    └── approve_submissions.py     # одобрение заявок из формы
```

---

## Каналы

| Канал | Язык | Переменная |
|---|---|---|
| @WrPtCy | RU | TELEGRAM_CHANNEL_ID |
| @partycy | EN | TELEGRAM_CHANNEL_EN |

Флаги в Firebase: `posted_tg` (RU), `posted_tg_en` (EN), `posted_threads`, `posted_instagram`

Лимит: **5 постов за цикл** на каждый канал. Цикл каждые **15 минут**.

---

## RSS источники (активные)

| Источник | Язык | Фильтр |
|---|---|---|
| vkcyprus.com/afisha/feed/ | RU | нет (870 событий) |
| afishamira.com/city/cyprus/feed/ | RU | нет |
| cyprus-mail.com/…/whats-on/feed/ | EN | да |
| parikiaki.com/feed/ | EN | да |
| en.philenews.com/feed/ | EN | да |
| kiprinform.com/en/feed/ | EN | да |
| timeout.com/… | EN | да |

**Отключены:** cyprus-mail-sport, cyprus-mail-athletics (новостные статьи, не афиша)

## Telegram источники (активные, Telethon)

cyprusit, hub_cy, cyproplan, LentaCypRus, Vestnik_Kipra, cyprus_kipr, evropakipr, cyprus_music, kipr_podslushano_limasol, kipr_podslushano_nicosia, yoga_cyprus, padelcyprus, Fractal_in_Cyprus, mamacyprus

**Отключены:** KouspoRun, CyprusRoadRaces, kidscyprus (username не найден)

---

## Данные события (поля в Firestore)

```python
{
  "id": "vkcyprus_saxophonistbaloo",
  "title": "...",
  "title_en": "...",
  "full_text": "...",
  "full_text_en": "...",
  "date": "19 Jun 2026",
  "venue": "",
  "city": "Limassol",
  "url": "https://...",
  "price": "",
  "photo_url": "https://...",
  "category": "music",
  "source": "vkcyprus",
  "created_at": "...",
  "posted_tg": false,
  "posted_tg_en": false,
  "posted_threads": false,
  "posted_instagram": false,
}
```

**9 категорий:** music, nightlife, art, food, sport, networking, culture, kids, outdoor

---

## Переменные окружения (Railway)

| Переменная | Назначение |
|---|---|
| TELEGRAM_BOT_TOKEN | бот |
| TELEGRAM_CHANNEL_ID | @WrPtCy |
| TELEGRAM_CHANNEL_EN | @partycy |
| TELEGRAM_API_ID | Telethon |
| TELEGRAM_API_HASH | Telethon |
| TG_SESSION_STRING | StringSession |
| FIREBASE_SERVICE_ACCOUNT_JSON | JSON строкой |
| THREADS_ACCESS_TOKEN | Threads API |
| THREADS_USER_ID | Threads user ID |

---

## Важные технические детали

- **firebase_admin** не работает на локальном Python 3.14 (конфликт httpx/cgi) — только на Railway Python 3.12
- **Скрипты через REST API** (`scripts/mark_all_posted_rest.py`, `scripts/preview_next_posts.py`) работают локально через `railway run`
- **Firestore composite index** нужен для `where + orderBy` — обходим сортировкой на клиенте
- **Фото** отправляются через multipart (скачиваем сами, шлём как файл) — прямые URL часто отклоняются Telegram
- **Переводы** только для событий которые идут в пост (5 штук) — не для всех 200+

---

## Роадмап

### Готово
- [x] RSS парсинг с извлечением фото, даты, города
- [x] Telegram парсинг (Telethon, 14 каналов)
- [x] Firebase хранение + автоочистка 30 дней
- [x] Fuzzy дедупликация (rapidfuzz, порог 88%)
- [x] Категоризация событий (9 категорий)
- [x] Постинг в TG RU + EN каналы (раздельные флаги)
- [x] Постинг в Threads (1 EN пост)
- [x] Мини-апп: фильтры, избранное, шара, умные даты
- [x] SEO лендинг (landing.html)
- [x] Форма добавления событий (submit.html)
- [x] Веб-админка (admin.html)
- [x] Фильтр качества (убирает новости, некрологи, политику)
- [x] Лимит 5 постов/цикл, цикл 15 минут

### В процессе
- [ ] Новые RSS источники (заведения Кипра)
- [ ] Описание и оформление каналов @WrPtCy / @partycy
- [ ] Удалить плохие старые посты из каналов

### Фаза 4 — Монетизация (после 1000 подписчиков)
- [ ] Продвижение событий в топ — платный pinned пост
- [ ] Партнёрство с заведениями — подписка €49/мес
- [ ] Реклама в TG канале

---

## Ссылки

- GitHub: `https://github.com/Andrew-qlead/where-party`
- Мини-апп: `https://andrew-qlead.github.io/where-party/`
- Лендинг: `https://andrew-qlead.github.io/where-party/landing.html`
- Админка: `https://andrew-qlead.github.io/where-party/admin.html`
- Firebase Console: `https://console.firebase.google.com/project/whereparty-88938`
- Railway: `https://railway.app/project/8190f2d8-e90f-4244-a113-4be1684c2549`
