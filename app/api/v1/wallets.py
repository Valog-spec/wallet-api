"""
Роутер API v1 для работы с кошельками.

Определяет эндпоинты создания, получения и операций над кошельками.
Эндпоинты защищены rate limiter-ом.
"""

import uuid

from fastapi import APIRouter, Request

from app.api.dependencies import WalletServiceDep
from app.limiter import limiter
from app.schemas.wallet import WalletOperation, WalletResponse

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.get("/{wallet_id}", response_model=WalletResponse)
@limiter.limit("30/minute")
async def get_wallet(
    request: Request,
    wallet_id: uuid.UUID,
    service: WalletServiceDep,
):
    """Получает текущий баланс кошелька по его UUID."""
    return await service.get_wallet(wallet_id)


@router.post("/{wallet_id}/operation", response_model=WalletResponse)
@limiter.limit("10/minute")
async def wallet_operation(
    request: Request,
    wallet_id: uuid.UUID,
    body: WalletOperation,
    service: WalletServiceDep,
):
    """Выполняет операцию пополнения (DEPOSIT) или снятия (WITHDRAW)."""
    return await service.perform_operation(
        wallet_id=wallet_id, operation_type=body.operation_type, amount=body.amount
    )


@router.post("", response_model=WalletResponse, status_code=201)
@limiter.limit("5/minute")
async def create_wallet(
    request: Request,
    service: WalletServiceDep,
):
    """Создает новый кошелёк с нулевым балансом."""
    return await service.create_wallet()
