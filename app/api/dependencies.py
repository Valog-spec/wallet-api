"""FastAPI dependencies.

Содержит зависимости и типизированные алиасы для внедрения в эндпоинты.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_session
from app.services.wallet import WalletService


def get_wallet_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WalletService:
    """Dependency для создания экземпляра WalletService."""
    return WalletService(session)


WalletServiceDep = Annotated[WalletService, Depends(get_wallet_service)]
