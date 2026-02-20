"""
Модель кошелька.

Описывает таблицу wallets в базе данных.
"""

import uuid
from decimal import Decimal

from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class Wallet(Base):
    """
    Кошелёк пользователя.

    Attributes:
        id: Уникальный идентификатор кошелька (UUID).
        balance: Текущий баланс кошелька с точностью до 2 знаков.
    """

    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2), default=Decimal("0.00")
    )
