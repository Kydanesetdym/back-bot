# BE Task 01 — Клиент-серверное приложение с авторизацией через Telegram-бота

Простое клиент-серверное приложение: клиент на **Flet** (desktop + web), сервер на **FastAPI**, Telegram-бот на **Aiogram 3** с **webhook** (через **ngrok**). Авторизация по 4-значному PIN-коду, который выдаёт бот командой `/start` (PIN действует 2 минуты).

## Стек

- **ClientApp:** Python + [Flet](https://flet.dev/) (последняя версия, `>=1.1.2`)
- **ServerApp:** FastAPI (эндпоинты `GET /health`, `POST /auth`, `GET /bot`, webhook)
- **Bot:** Aiogram 3, webhook (обязательно), команда `/start`
- **Туннель для webhook:** ngrok
- **Хранение PIN/пользователей:** in-memory (TTL PIN — 120 секунд, одноразовый)

## Структура проекта

```text
.
├─ server/               # FastAPI + Aiogram (webhook, handlers, логика PIN)
│  ├─ main.py            # приложение, /health, /auth, /bot, /webhook/telegram
│  ├─ bot.py             # /start, получение профиля/аватара из Telegram
│  ├─ storage.py         # in-memory хранилище PIN (TTL 2 мин, one-time)
│  ├─ config.py          # конфигурация из .env
│  └─ run_ngrok.py       # запуск сервера с автоматическим ngrok-туннелем
├─ client/
│  └─ main.py            # Flet-клиент (LoginWindow, MainWindow), desktop + web
├─ assets/
│  └─ placeholder_avatar.png  # заглушка, если у пользователя нет фото
├─ tests/                # pytest (логика PIN, API health/auth)
├─ .env                  # переменные окружения (токены/настройки)
├─ .env.example          # пример конфигурации
├─ requirements.txt
└─ README.md
```

## Требования

- Python 3.11+
- Аккаунт ngrok и authtoken (для webhook)
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))

## Установка

1. Создайте и активируйте виртуальное окружение (рекомендуется):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Установите зависимости:

   ```powershell
   pip install -r requirements.txt
   ```

3. Настройте `.env` (файл уже может быть создан; проверьте значения):

   ```env
   BOT_TOKEN=<токен_бота>
   NGROK_AUTHTOKEN=<токен_ngrok>
   BOT_USERNAME=            # опционально: определится автоматически при старте сервера
   BASE_URL=                # публичный https URL ngrok (заполняется автоматически при run_ngrok.py)
   SERVER_HOST=127.0.0.1
   SERVER_PORT=8000
   WEBHOOK_PATH=/webhook/telegram
   SERVER_PUBLIC_URL=http://127.0.0.1:8000
   ```

   - `BOT_USERNAME` можно не задавать — сервер получает его через `getMe` при запуске.
   - `SERVER_PUBLIC_URL` — адрес сервера, к которому подключается клиент (по умолчанию `http://127.0.0.1:8000`).

## Запуск

### 1. Запуск сервера с webhook через ngrok

**Вариант A (рекомендуется, автоматически):** сервер сам поднимет ngrok-туннель, установит `BASE_URL` и зарегистрирует webhook:

```powershell
python -m server.run_ngrok
```

Скрипт использует `NGROK_AUTHTOKEN` из `.env`, выводит публичный URL и запускает FastAPI на `SERVER_HOST:SERVER_PORT`.

**Вариант B (вручную):**

1. Запустите ngrok в отдельном терминале:
   ```powershell
   ngrok http 8000
   ```
2. Скопируйте выданный `https://...ngrok...` URL в `.env` как `BASE_URL=https://...`
3. Запустите сервер:
   ```powershell
   python -m server.main
   ```
   При старте сервер установит webhook на `${BASE_URL}${WEBHOOK_PATH}`.

Проверка сервера:
- `GET http://127.0.0.1:8000/health` → `{"status":"ok"}`
- `GET http://127.0.0.1:8000/bot` → `{"username":"...","url":"https://t.me/..."}`

### 2. Запуск клиента (Flet)

Убедитесь, что сервер запущен и `SERVER_PUBLIC_URL` в `.env` указывает на него.

**Desktop:**
```powershell
python -m client.main
# или
flet run client/main.py
```

**Web:**
```powershell
python -m client.main --web
# или (порт по умолчанию 8550, можно задать FLET_WEB_PORT)
$env:FLET_WEB=1; python -m client.main
```

В окне входа:
- Поле **«Ключ (PIN-код)»** — введите 4-значный PIN из бота.
- Кнопка **«Войти»** — авторизация через `POST /auth`.
- Ссылка **«Перейти в Telegram-бота»** — открывает бота в браузере (`t.me/<username>`).

После успешного входа отображаются: **Имя**, **Фамилия**, **Юзернейм**, **Аватар** (или заглушка, если фото отсутствует).

## Поток авторизации

1. Пользователь открывает бота и отправляет `/start`.
2. Бот берёт данные профиля Telegram (имя, фамилия, username, фото), генерирует 4-значный PIN и сохраняет его в памяти на **2 минуты**.
3. Бот отправляет PIN пользователю.
4. Клиент отправляет `POST /auth` с телом `{"key":"1234"}`.
5. Сервер возвращает данные пользователя и удаляет PIN (одноразовое использование). Неверный/истёкший PIN → `401`.

## API

- `GET /health` → `200 {"status":"ok"}`
- `POST /auth` body `{"key":"1234"}` → `200 {first_name,last_name,username,avatar}` | `401`
- `GET /bot` → `200 {"username":"...","url":"https://t.me/..."}` (для ссылки в клиенте)
- `POST /webhook/telegram` — endpoint для Telegram webhook

## Тесты

Тесты не требуют реальный Telegram/ngrok (используются in-memory логика и моки окружения).

```powershell
python -m pytest -q
```

Покрытие тестами: генерация/TTL/одноразовость PIN, истечение, `health`, `auth` (успех/неверный/истёкший PIN/валидация).

## Примечания

- Данные (PIN и профили) хранятся **в памяти процесса** и теряются при перезапуске сервера.
- Для работы webhook нужен публичный **HTTPS** URL (ngrok). Без `BASE_URL` сервер стартует, но webhook не регистрируется.
- Если у пользователя Telegram нет фамилии/username/фото — в клиенте показывается прочерк для текстовых полей и заглушка для аватара.
- Токены в `.env` не следует публиковать в открытых репозиториях.
