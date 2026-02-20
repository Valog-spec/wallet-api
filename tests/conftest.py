"""
Фикстуры для тестов Wallet API.

Настраивает тестовую БД, HTTP-клиент и вспомогательные фикстуры
для создания кошельков.
"""

from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.configs.config import settings
from app.database.database import Base, get_session
from app.limiter import limiter
from app.main import app
from app.models.wallet import Wallet  # noqa: F401

limiter.enabled = False


@pytest.fixture(autouse=True)
async def setup_db():
    """Подготовить таблицы и очистить данные через TRUNCATE между тестами."""
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE wallets CASCADE"))
    await engine.dispose()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Асинхронный HTTP-клиент для тестирования эндпоинтов."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def wallet_id(client: AsyncClient) -> str:
    """Создать пустой кошелёк и вернуть его UUID."""
    response = await client.post("/api/v1/wallets")
    return response.json()["id"]


@pytest.fixture
async def funded_wallet_id(client: AsyncClient) -> str:
    """Создать кошелёк с балансом 5000.00 и вернуть его UUID."""
    response = await client.post("/api/v1/wallets")
    wid = response.json()["id"]
    await client.post(
        f"/api/v1/wallets/{wid}/operation",
        json={"operation_type": "DEPOSIT", "amount": str(Decimal("5000.00"))},
    )
    return wid
