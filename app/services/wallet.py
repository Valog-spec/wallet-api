"""
Сервисный слой для бизнес-логики работы с кошельками.

Содержит валидацию, обработку операций и управление транзакциями.
"""

import logging
import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet import Wallet
from app.repositories.wallet import WalletRepository
from app.schemas.wallet import OperationType

logger = logging.getLogger("wallet_api")


class WalletService:
    """Сервис для управления кошельками.

    Реализует бизнес-логику операций пополнения и снятия средств.

    Args:
        session: Асинхронная сессия SQLAlchemy.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = WalletRepository(session)

    async def get_wallet(self, wallet_id: uuid.UUID) -> Wallet:
        """Получить кошелёк по идентификатору.

        Args:
            wallet_id: UUID кошелька.

        Returns:
            Объект Wallet.

        Raises:
            HTTPException: 404, если кошелёк не найден.
        """
        wallet = await self.repo.get_by_id(wallet_id)
        if wallet is None:
            logger.warning("Кошелёк не найден: %s", wallet_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found",
            )
        logger.debug("Кошелёк получен: %s, баланс: %s", wallet_id, wallet.balance)
        return wallet

    async def perform_operation(
        self,
        wallet_id: uuid.UUID,
        operation_type: OperationType,
        amount: Decimal,
    ) -> Wallet:
        """
        Выполнить операцию пополнения или снятия средств.

        Использует блокировку строки (SELECT FOR UPDATE) для
        корректной работы при параллельных запросах.

        Args:
            wallet_id: UUID кошелька.
            operation_type: Тип операции (DEPOSIT / WITHDRAW).
            amount: Сумма операции.

        Returns:
            Обновлённый объект Wallet.

        Raises:
            HTTPException: 404, если кошелёк не найден.
            HTTPException: 400, если недостаточно средств для снятия.
        """
        wallet = await self.repo.get_by_id_with_lock(wallet_id)
        if wallet is None:
            logger.warning("Кошелёк не найден для операции: %s", wallet_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found",
            )

        if operation_type == OperationType.DEPOSIT:
            new_balance = wallet.balance + amount
        else:
            new_balance = wallet.balance - amount
            if new_balance < 0:
                logger.warning(
                    "Недостаточно средств: кошелёк=%s, баланс=%s, сумма=%s",
                    wallet_id,
                    wallet.balance,
                    amount,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Insufficient funds",
                )

        wallet = await self.repo.update_balance(wallet, new_balance)
        await self.session.commit()
        logger.info(
            "%s: кошелёк=%s, сумма=%s, новый_баланс=%s",
            operation_type.value,
            wallet_id,
            amount,
            wallet.balance,
        )
        return wallet

    async def create_wallet(self, balance: Decimal = Decimal("0.00")) -> Wallet:
        """
        Создать новый кошелёк.

        Args:
            balance: Начальный баланс (по умолчанию 0.00).

        Returns:
            Созданный объект Wallet.
        """
        wallet = await self.repo.create(balance)
        await self.session.commit()
        logger.info("Кошелёк создан: %s", wallet.id)
        return wallet
