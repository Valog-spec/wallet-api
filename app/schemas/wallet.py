"""
Pydantic-схемы для работы с кошельками.

Содержит схемы запросов и ответов API.
"""

import uuid
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class OperationType(str, Enum):
    """Тип операции над кошельком."""

    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"


class WalletOperation(BaseModel):
    """
    Схема запроса на изменение баланса кошелька.

    Attributes:
        operation_type: Тип операции (DEPOSIT или WITHDRAW).
        amount: Сумма операции (строго больше нуля).
    """

    operation_type: OperationType
    amount: Decimal = Field(gt=0)


class WalletResponse(BaseModel):
    """
    Схема ответа с данными кошелька.

    Attributes:
        id: UUID кошелька.
        balance: Текущий баланс.
    """

    id: uuid.UUID
    balance: Decimal

    model_config = {"from_attributes": True}
