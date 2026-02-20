# Wallet API

REST API для управления кошельками пользователей. Поддерживает пополнение, снятие средств и получение баланса.

## Стек технологий

- **Python 3.12**
- **FastAPI** — веб-фреймворк
- **SQLAlchemy 2.0** — ORM (async)
- **PostgreSQL** — база данных
- **Alembic** — миграции
- **asyncpg** — асинхронный драйвер PostgreSQL
- **PDM** — менеджер зависимостей
- **Docker / Docker Compose** — контейнеризация
- **pytest + httpx + pytest-cov** — тестирование
- **slowapi** — rate limiting
- **ruff** — линтер и форматтер

## Архитектура

Трёхслойная архитектура:

```
Router (api/v1/wallets.py)  →  Service (services/wallet.py)  →  Repository (repositories/wallet.py)
```

- **Router** — обработка HTTP-запросов, валидация входных данных через Pydantic
- **Service** — бизнес-логика, управление транзакциями
- **Repository** — SQL-запросы к базе данных

### Конкурентность

Для корректной обработки параллельных запросов к одному кошельку используется пессимистическая блокировка `SELECT ... FOR UPDATE` на уровне PostgreSQL. Это гарантирует, что параллельные операции над одним кошельком выполняются последовательно, предотвращая race condition.

#### Возможные улучшения для production

В текущей реализации пессимистическая блокировка полностью покрывает требования задания. Однако для production-системы работы с финансами стоит рассмотреть:

- **Журнал транзакций (ledger)** — отдельная таблица с историей всех операций. Баланс вычисляется как сумма записей, что обеспечивает полный аудит и возможность восстановления при сбоях.
- **Идемпотентность** — передача `idempotency_key` клиентом для защиты от двойных списаний при повторных запросах (ретраях).
- **Уровень изоляции `SERIALIZABLE`** — самый строгий уровень изоляции PostgreSQL для критичных финансовых операций.

### Rate Limiting

Эндпоинты защищены от злоупотреблений через `slowapi`:

| Эндпоинт | Лимит |
|----------|-------|
| `GET /wallets/{id}` | 30/мин |
| `POST /wallets/{id}/operation` | 10/мин |
| `POST /wallets` | 5/мин |

### Логирование

Логи записываются в файлы в зависимости от уровня:

| Файл | Уровень |
|------|---------|
| `logger.log` | DEBUG, INFO |
| `calc_warning.log` | WARNING |
| `calc_error.log` | ERROR |
| `calc_exception.log` | Исключения с traceback |

## Структура проекта

```
├── app/
│   ├── api/
│   │   ├── dependencies.py      # FastAPI Depends
│   │   └── v1/wallets.py        # Эндпоинты
│   ├── configs/config.py        # Конфигурация (env)
│   ├── database/database.py     # Подключение к БД, Base
│   ├── logger/
│   │   ├── config.py            # Конфигурация логирования
│   │   └── log_files/           # Файлы логов
│   ├── models/wallet.py         # SQLAlchemy-модель
│   ├── repositories/wallet.py   # Работа с БД
│   ├── schemas/wallet.py        # Pydantic-схемы
│   ├── services/wallet.py       # Бизнес-логика
│   ├── limiter.py               # Rate limiter
│   └── main.py                  # Точка входа FastAPI
├── alembic/                     # Миграции
├── tests/                       # Тесты
├── .github/workflows/ci.yml     # CI/CD (GitHub Actions)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml               # Зависимости (PDM)
└── pytest.ini
```

## Запуск

### Docker Compose (рекомендуемый способ)

```bash
docker-compose up --build
```

Приложение будет доступно на `http://localhost:8000`.
Миграции применяются автоматически при старте контейнера.

### Локально

```bash
pdm install
pdm run alembic upgrade head
pdm run uvicorn app.main:app --reload
```

## API

### Создать кошелёк

```
POST /api/v1/wallets
```

Ответ:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "balance": 0.00
}
```

### Получить баланс

```
GET /api/v1/wallets/<WALLET_UUID>
```

Ответ:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "balance": 1000.00
}
```

### Изменить баланс

```
POST /api/v1/wallets/<WALLET_UUID>/operation
```

Тело запроса:
```json
{
  "operation_type": "DEPOSIT",
  "amount": 1000
}
```

`operation_type` — `DEPOSIT` (пополнение) или `WITHDRAW` (снятие).

При превышении лимита запросов возвращается `429 Too Many Requests`.

## Тестирование

Для запуска тестов необходима запущенная база данных PostgreSQL:

```bash
docker-compose up -d db
pdm run pytest
```

### Покрытие кода

Покрытие тестами: **83%** (порог в CI: 80%).

При запуске `pytest` автоматически выводится отчёт по покрытию (`--cov=app --cov-report=term-missing`).

Тесты покрывают:
- Создание кошелька
- Получение баланса
- Пополнение и снятие средств
- Снятие при недостаточном балансе
- Несуществующий кошелёк
- Невалидные данные
- Конкурентные операции (параллельные пополнения и снятия)

## Линтинг

```bash
pdm run ruff check app/ tests/
pdm run ruff format app/ tests/
```

## CI/CD

GitHub Actions автоматически запускает при push/PR в main:
1. **Lint** — `ruff check` + `ruff format --check`
2. **Tests** — `pytest` с PostgreSQL в service container
3. **Coverage** — проверка порога покрытия (минимум 80%)

## Переменные окружения

| Переменная    | По умолчанию | Описание              |
|---------------|-------------|------------------------|
| `DB_HOST`     | `localhost` | Хост базы данных       |
| `DB_PORT`     | `5432`      | Порт базы данных       |
| `DB_USER`     | `postgres`  | Пользователь БД        |
| `DB_PASSWORD` | `postgres`  | Пароль БД              |
| `DB_NAME`     | `wallet_db` | Имя базы данных        |
