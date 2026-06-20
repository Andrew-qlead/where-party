# WR PT — Where Party Cyprus · Контекст проекта

## Суть проекта
Агрегатор событий Кипра с автораспределением по каналам.
Парсер собирает события → Firebase → Telegram каналы (RU+EN) + Мини-апп + Threads + FlutterFlow-приложение.

---

## Стек

| Компонент | Технология |
|---|---|
| Бэкенд / парсер | Python 3, Railway (worker.py, каждые 2ч) |
| База данных | Firebase Firestore (проект: `whereparty-88938`) |
| Мини-апп | HTML/JS, GitHub Pages: `andrew-qlead.github.io/where-party/` |
| TG-бот | python-telegram-bot, long polling |
| Хостинг бота | Railway, сервис `pacific-forgiveness` |
| Социальные сети | Threads API (`@iseealleye`), TG каналы |
| Переводы | deep-translator (Google Translate, без ключа) |
| FlutterFlow | отдельный аккаунт, читает тот же Firebase |

---

## Структура файлов

```
/Users/illaviktorovna/where-party/
├── main.py                    # главный запуск: парсинг → категоризация → перевод → Firebase → посты
├── worker.py                  # Railway: бот-поток + main.py каждые 2ч
├── requirements.txt
├── railway.json               # start: python worker.py
│
├── parsers/
│   ├── telegram_parser.py     # Telethon, SOURCE_CHANNELS (18 каналов)
│   ├── web_parser.py          # RSS: vkcyprus, afishamira, cyprus-mail×3, parikiaki, philenews, kiprinform
│   ├── eventbrite_parser.py
│   ├── incyprus_parser.py
│   └── timeout_parser.py
│
├── db/
│   ├── firebase.py            # get_db, save_events_batch, mark_posted, get_unposted
│   ├── categorizer.py         # weighted keywords (RU+EN), title×3 приоритет
│   └── city_extractor.py      # ← НАЧАТО, не закончено (извлечение города из текста)
│
├── bot/
│   ├── bot_server.py          # long-poll бот, /start → кнопка "тык" → мини-апп
│   ├── poster.py              # post_new_events → @WrPtCy
│   ├── formatter_en.py        # EN форматтер для второго канала
│   └── translator.py          # translate_to_english() через deep-translator
│
├── social/
│   └── threads_poster.py      # post_event_bilingual() → Threads RU потом EN
│
└── miniapp/
    ├── index.html             # мини-апп (карточки, модалка, карта Leaflet, RU/EN, фильтр категорий)
    └── firebase-config.js     # конфиг Firebase для JS SDK
```

---

## Данные события (поля в Firestore)

```python
{
  "id": "tg_cyprusit_123",       # уникальный ID
  "title": "...",                 # заголовок RU
  "title_en": "...",              # заголовок EN (Google Translate)
  "full_text": "...",             # описание RU
  "full_text_en": "...",          # описание EN
  "date": "20 Jun 2026",          # дата строкой
  "venue": "...",                 # место
  "city": "Limassol",            # город (пока часто "Cyprus")
  "url": "https://...",           # ссылка на билеты/подробности
  "price": "",                    # цена
  "photo_url": "",               # ← ПУСТО, нужно заполнить
  "category": "music",           # категория (9 штук + other)
  "source": "tg",                # источник
  "created_at": "...",            # ISO timestamp
  "posted_tg": false,
  "posted_threads": false,
}
```

**9 категорий:** music, nightlife, art, food, sport, networking, culture, kids, outdoor

---

## Мини-апп (miniapp/index.html)

**Что работает:**
- Список событий из Firebase (limit 150)
- Фильтр по категориям (горизонтальный скролл)
- Поиск по тексту
- RU/EN переключение (title_en, full_text_en)
- Детальная модалка при тапе на карточку
- Вкладка "Скоро" (сортировка по дате)
- Вкладка "Карта" (Leaflet/OpenStreetMap, маркеры по городу)
- Фильтр прошедших событий (isExpired)

**Что НЕ сделано (следующие задачи):**
- Фото в карточках (photo_url пустой)
- Фильтр по городу (кнопки Лимасол/Никосия/Ларнака/Пафос)
- Умные даты ("Сегодня", "Завтра", "Эта пятница")
- Кнопка "Поделиться" (Telegram.WebApp.shareUrl)
- Вкладка "Избранное" (localStorage)

---

## Источники данных

### Telegram-каналы (Telethon + StringSession)
```python
SOURCE_CHANNELS = [
    "cyprusit", "hub_cy",                          # IT
    "cyproplan", "LentaCypRus", "Vestnik_Kipra",   # Афиша
    "cyprus_kipr", "evropakipr", "cyprus_music",
    "kipr_podslushano_limasol", "kipr_podslushano_nicosia",
    "KouspoRun", "CyprusRoadRaces",                # Спорт
    "yoga_cyprus", "padelcyprus",
    "Fractal_in_Cyprus", "kidscyprus", "mamacyprus", # Дети
]
```

### RSS-сайты
| URL | Контент |
|---|---|
| vkcyprus.com/afisha/feed/ | 870 событий, RU, главная русская афиша |
| afishamira.com/city/cyprus/feed/ | RU концерты |
| cyprus-mail.com/category/entertainment/whats-on/feed/ | EN афиша |
| cyprus-mail.com/category/sport/feed/ | EN спорт |
| cyprus-mail.com/category/athletics/feed/ | EN лёгкая атлетика |
| parikiaki.com/feed/ | EN/GR общие |
| en.philenews.com/feed/ | EN новости (с фильтром) |
| kiprinform.com/en/feed/ | EN |

---

## Переменные окружения (Railway)

| Переменная | Назначение |
|---|---|
| TELEGRAM_BOT_TOKEN | бот @WrPtCy |
| TELEGRAM_CHANNEL | @WrPtCy (RU канал) |
| TELEGRAM_CHANNEL_EN | EN канал (если есть) |
| TELEGRAM_API_ID | Telethon API |
| TELEGRAM_API_HASH | Telethon API |
| TG_SESSION_STRING | StringSession для Railway |
| FIREBASE_SERVICE_ACCOUNT_JSON | JSON строкой |
| THREADS_ACCESS_TOKEN | Threads API |
| THREADS_USER_ID | Threads user ID |

---

## Роадмап (что делать дальше)

### Фаза 1 — Качество данных (В ПРОЦЕССЕ)
- [ ] **Фото к событиям** — извлекать `<media:thumbnail>` из RSS, сохранять `photo_url` в Firebase, показывать в карточках
- [ ] **Извлечение города** — `city_extractor.py` начат, нужно подключить в `main.py`
- [ ] **Автоочистка Firebase** — удалять события старше 30 дней в `main.py`
- [ ] **Умная дедупликация** — fuzzy match по заголовкам (библиотека `rapidfuzz`)

### Фаза 2 — Мини-апп UX
- [ ] **Фильтр по городу** — кнопки Лимасол/Никосия/Ларнака/Пафос над категориями
- [ ] **Умные даты** — "Сегодня", "Завтра", "Эта пятница" вместо "20 Jun 2026"
- [ ] **Кнопка "Поделиться"** — `Telegram.WebApp.shareUrl(url, text)`
- [ ] **Избранное** — localStorage, отдельная вкладка вместо или рядом со "Скоро"

### Фаза 3 — Рост
- [ ] **Instagram автопостинг** — нужен Professional аккаунт → Graph API
- [ ] **SEO-лендинг whereparty.cy** — статика с афишей, органика из Google
- [ ] **Форма "Добавить событие"** — заведения сами постят → Firebase

### Фаза 4 — Монетизация
- [ ] **Продвижение событий в топ** — платный pinned пост
- [ ] **Партнёрство с заведениями** — подписка €49/мес
- [ ] **Реклама в TG-канале** — когда 1000+ подписчиков

---

## Важные детали

- **GitHub**: `https://github.com/Andrew-qlead/where-party`
- **Ветка gh-pages**: содержит `index.html` + `firebase-config.js` для GitHub Pages
- **Netlify**: wrpt-miniapp.netlify.app — кредиты закончились, переехали на GitHub Pages
- **Railway**: сервис `pacific-forgiveness`, проект `pacific-forgiveness`
- **Firestore Rules**: `allow read: if true` — публичные чтения открыты
- **BotFather Menu Button**: URL = `https://andrew-qlead.github.io/where-party/`
- **FlutterFlow**: другой аккаунт, читает тот же Firebase `whereparty-88938`
- **Meta App**: WrPt Cyprus, App ID `1735363441147335`, Threads tester: @iseealleye
- **deep-translator**: используется вместо deepl (Python 3.14 совместим)
- **firebase_admin**: НЕ работает на локальном Python 3.14 (конфликт httpx/cgi), работает только на Railway (Python 3.11)

---

## Стиль мини-апп

Тёмная тема, золотой акцент:
- `--espresso: #2B2A1A` — фон
- `--gold: #C9A84C` — акцент
- `--limestone: #F2EDE2` — текст
- Шрифт заголовков: EB Garamond
- Карточки: border-radius 12px, левая цветная полоска по категории
