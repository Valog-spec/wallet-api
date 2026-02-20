"""
Репозиторий для работы с кошельками в базе данных.

Инкапсулирует все SQL-запросы к таблице wallets.
"""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet import Wallet


class WalletRepository:
    """
    Репозиторий для работы с кошелком

    Args:
        session: Асинхронная сессия SQLAlchemy.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, wallet_id: uuid.UUID) -> Wallet | None:
        """Получить кошелёк по UUID.

        Args:
            wallet_id: Идентификатор кошелька.

        Returns:
            Объект Wallet или None, если не найден.
        """
        stmt = select(Wallet).where(Wallet.id == wallet_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_lock(self, wallet_id: uuid.UUID) -> Wallet | None:
        """
        Получить кошелёк по UUID с блокировкой строки (SELECT FOR UPDATE).

        Используется для безопасного изменения баланса
        в конкурентной среде.

        Args:
            wallet_id: Идентификатор кошелька.

        Returns:
            Объект Wallet или None, если не найден.
        """
        stmt = select(Wallet).where(Wallet.id == wallet_id).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, balance: Decimal = Decimal("0.00")) -> Wallet:
        """Создать новый кошелёк.

        Args:
            balance: Начальный баланс (по умолчанию 0.00).

        Returns:
            Созданный объект Wallet.
        """
        wallet = Wallet(balance=balance)
        self.session.add(wallet)
        await self.session.flush()
        return wallet

    async def update_balance(self, wallet: Wallet, new_balance: Decimal) -> Wallet:
        """Обновить баланс кошелька.

        Args:
            wallet: Объект кошелька для обновления.
            new_balance: Новое значение баланса.

        Returns:
            Обновлённый объект Wallet.
        """
        wallet.balance = new_balance
        await self.session.flush()
        return wallet
