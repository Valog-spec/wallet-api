"""
Тесты эндпоинтов Wallet API.

Покрывает CRUD-операции, валидацию, обработку ошибок
и корректность работы в конкурентной среде.
"""

import asyncio
from decimal import Decimal

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_create_wallet(client: AsyncClient):
    """Создание кошелька возвращает 201 и нулевой баланс."""
    response = await client.post("/api/v1/wallets")
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert Decimal(data["balance"]) == Decimal("0.00")


async def test_get_wallet(client: AsyncClient, wallet_id: str):
    """Получение существующего кошелька возвращает его UUID и баланс."""
    response = await client.get(f"/api/v1/wallets/{wallet_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == wallet_id
    assert Decimal(data["balance"]) == Decimal("0.00")


async def test_get_wallet_not_found(client: AsyncClient):
    """Запрос несуществующего кошелька возвращает 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/v1/wallets/{fake_id}")
    assert response.status_code == 404


async def test_deposit(client: AsyncClient, wallet_id: str):
    """Пополнение увеличивает баланс на указанную сумму."""
    response = await client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        json={"operation_type": "DEPOSIT", "amount": "1000.00"},
    )
    assert response.status_code == 200
    assert Decimal(response.json()["balance"]) == Decimal("1000.00")


async def test_withdraw(client: AsyncClient, funded_wallet_id: str):
    """Снятие уменьшает баланс на указанную сумму."""
    response = await client.post(
        f"/api/v1/wallets/{funded_wallet_id}/operation",
        json={"operation_type": "WITHDRAW", "amount": "2000.00"},
    )
    assert response.status_code == 200
    assert Decimal(response.json()["balance"]) == Decimal("3000.00")


async def test_withdraw_insufficient_funds(client: AsyncClient, wallet_id: str):
    """Снятие при недостаточном балансе возвращает 400."""
    response = await client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        json={"operation_type": "WITHDRAW", "amount": "100.00"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient funds"


async def test_invalid_amount(client: AsyncClient, wallet_id: str):
    """Отрицательная сумма операции возвращает 422 (ошибка валидации)."""
    response = await client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        json={"operation_type": "DEPOSIT", "amount": "-100"},
    )
    assert response.status_code == 422


async def test_operation_not_found_wallet(client: AsyncClient):
    """Операция над несуществующим кошельком возвращает 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.post(
        f"/api/v1/wallets/{fake_id}/operation",
        json={"operation_type": "DEPOSIT", "amount": "100.00"},
    )
    assert response.status_code == 404


async def test_concurrent_deposits(client: AsyncClient, wallet_id: str):
    """
    10 параллельных пополнений по 100 дают итоговый баланс 1000.

    Проверяет корректность блокировки строки (SELECT FOR UPDATE)
    при конкурентных операциях записи.
    """

    async def deposit():
        return await client.post(
            f"/api/v1/wallets/{wallet_id}/operation",
            json={"operation_type": "DEPOSIT", "amount": "100.00"},
        )

    results = await asyncio.gather(*[deposit() for _ in range(10)])
    for r in results:
        assert r.status_code == 200

    response = await client.get(f"/api/v1/wallets/{wallet_id}")
    assert Decimal(response.json()["balance"]) == Decimal("1000.00")


async def test_concurrent_withdrawals(client: AsyncClient, funded_wallet_id: str):
    """
    7 параллельных снятий по 1000 с баланса 5000: 5 успешных, 2 отказа.

    Проверяет, что блокировка строки не допускает отрицательный баланс
    даже при одновременных запросах.
    """

    async def withdraw():
        return await client.post(
            f"/api/v1/wallets/{funded_wallet_id}/operation",
            json={"operation_type": "WITHDRAW", "amount": "1000.00"},
        )

    results = await asyncio.gather(*[withdraw() for _ in range(7)])
    success = [r for r in results if r.status_code == 200]
    failed = [r for r in results if r.status_code == 400]

    assert len(success) == 5
    assert len(failed) == 2

    response = await client.get(f"/api/v1/wallets/{funded_wallet_id}")
    assert Decimal(response.json()["balance"]) == Decimal("0.00")
