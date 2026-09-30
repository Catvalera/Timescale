# Timescale — микросервисы на FastAPI + React

Сервис загрузки CSV-замеров (порт C#-проекта `Web_api_Csharp`), к которому добавлены:

- **auth-service** — регистрация и вход по почте и паролю с подтверждением кодом из письма, JWT-токены;
- **mail-service** — отправка писем: код подтверждения, «регистрация завершена», «выполнен вход»;
- **frontend** — React-интерфейс: регистрация, вход, ввод кода, загрузка CSV, фильтры, очистка таблиц.

Структура auth-service и mail-service повторяет структуру присланных примеров (`src/core/...`, `ResultData`, `ServiceError`, SQLModel, Alembic, fastapi-mail + Jinja2).

```
                    ┌────────────────────────── frontend (nginx :3000) ──────────────────────────┐
  браузер ────────► │  /            → React (SPA)                                               │
                    │  /api/auth/*  → auth-service       :8000/api/*                            │
                    │  /api/data/*  → timescale-service  :8000/*                                │
                    └───────────────────────────────┬───────────────────────────┬───────────────┘
                                                    │                           │
                       ┌──────────── auth-service ──┴──┐         ┌── timescale-service ──┐
                       │ users, verify (схема auth)    │         │ Values, Results        │
                       │ выпускает JWT                 │         │ проверяет JWT (подпись │
                       └───────┬───────────────┬───────┘         │ общим SECRET_KEY)      │
                               │ HTTP          │                 └──────────┬─────────────┘
                     ┌─────────▼────────┐      │                            │
                     │   mail-service   │      └──────── PostgreSQL ────────┘
                     │ fastapi-mail+Jinja│               (timescale_db: схемы auth и public)
                     └─────────┬────────┘
                               │ SMTP
                        Mailpit / реальный SMTP
```

## Как работает авторизация

| Шаг | Запрос | Ответ |
|---|---|---|
| Регистрация | `POST /api/registration` `{full_name, email, nickname, password}` | письмо с кодом; `token.access_token` — **verify-токен** (10 мин), `data.requires_verification = true` |
| Вход | `POST /api/login` `{email, password}` | письмо с кодом; verify-токен. Если почта не подтверждена — код регистрации (`data.purpose = "registration"`) |
| Подтверждение | `POST /api/verify` `{code}` + заголовок `X-Access-Token: <verify-токен>` | пара `access_token` + `refresh_token`, данные пользователя; письмо «регистрация завершена» или «выполнен вход» |
| Повтор кода | `POST /api/verify/resend` + verify-токен | новый код (не чаще раза в 60 с), старый перестаёт действовать |
| Обновление | `POST /api/tokens/refresh` + `X-Refresh-Token` | новая пара токенов |
| Профиль | `GET /api/user/get-data` + `X-Access-Token` | ФИО, почта, никнейм, даты (без хеша пароля) |
| Выход | `POST /api/logout` + `X-Access-Token` | пустая пара токенов |

Все ответы auth-service и mail-service имеют вид `{"status", "data", "token", "error": {"code", "log"}}`.

**Безопасность**
- пароль хранится как хеш **argon2id**; код — как HMAC-SHA256 (сам код в БД не лежит);
- код из 6 цифр (`secrets`), действует 10 минут, 5 неверных попыток — и нужен новый код;
- verify-токен имеет отдельный тип `verify`: с ним нельзя обратиться ни к API данных, ни к профилю, только подтвердить код;
- если mail-service недоступен, регистрация откатывается целиком (503), пользователь не «зависает»;
- письма об успешной регистрации/входе отправляются в фоне и не блокируют ответ;
- timescale-service проверяет только подпись, срок, издателя и тип токена — в БД авторизации он не ходит.

## Запуск через Docker (рекомендуется)

```bash
cp .env.example .env          # поменяйте SECRET_KEY
docker compose up --build
```

| Что | Адрес |
|---|---|
| Приложение | http://localhost:3000 |
| Входящие письма (Mailpit) | http://localhost:8025 |
| Swagger auth-service | http://localhost:8001/docs |
| Swagger timescale-service | http://localhost:5145/swagger (кнопка Authorize → access-токен) |

По умолчанию письма никуда не уходят, их перехватывает Mailpit — коды смотрите на http://localhost:8025.
Чтобы отправлять настоящие письма, раскомментируйте SMTP-настройки в `.env` (пример для Яндекса там же; для Gmail: `smtp.gmail.com`, порт 587, `EMAIL_STARTTLS=true`, пароль приложения).

Миграции обоих сервисов применяются автоматически при старте контейнеров.

## Запуск без Docker

Нужны Python 3.12+, Node.js 20+, PostgreSQL и любой тестовый SMTP (например, [Mailpit](https://mailpit.axllent.org/) — порт 1025, веб-интерфейс 8025).

```bash
# 1. База
createdb -U postgres timescale_db

# 2. mail-service  → http://localhost:8002/docs
cd mail-service
python -m venv .venv && .venv\Scripts\activate      # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                                # Linux/macOS: cp
uvicorn src.main:app --port 8002

# 3. auth-service  → http://localhost:8001/docs
cd auth-service
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn src.main:app --port 8001

# 4. timescale-service  → http://localhost:5145/swagger
cd timescale-service
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --port 5145

# 5. frontend  → http://localhost:5173
cd frontend
npm install
npm run dev
```

Vite проксирует `/api/auth` и `/api/data` на сервисы так же, как nginx в Docker, поэтому CORS настраивать не нужно.

`SECRET_KEY` в `auth-service/.env` и `timescale-service/.env` должен совпадать.

## Структура

```
auth-service/
├── src/
│   ├── auth/          router, schemas, service (регистрация, вход, подтверждение), results
│   ├── users/         models (User, Verify), core, service, router (/user/get-data)
│   └── core/          config, database (SQLModel + DatabaseMethods), errors, results,
│                      security (TokenService), http (клиент к mail-service), email
├── alembic/           миграции (схема auth)
└── tests/
mail-service/
├── src/email/         router (/api/send/...), schemas, service (fastapi-mail)
├── src/core/          config, errors, results
├── templates/         base.html, verification.html, success-registration.html, success-login.html
└── tests/
timescale-service/     API данных из C#-проекта + проверка JWT (app/auth.py)
frontend/              React + Vite + TypeScript, nginx.conf (шлюз)
Tests data files/      тестовые CSV
docker-compose.yml
```

## Тесты

```bash
createdb -U postgres auth_service_test
createdb -U postgres timescale_db_test

cd mail-service      && pip install -r requirements-dev.txt && pytest   # поднимает SMTP-сервер в процессе
cd auth-service      && pip install -r requirements-dev.txt && pytest   # mail-service подменён заглушкой
cd timescale-service && pip install -r requirements-dev.txt && pytest
```
