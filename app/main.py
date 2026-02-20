"""
Точка входа приложения FastAPI.

Создаёт экземпляр приложения, подключает роутеры, rate limiter и логирование.
"""

import logging
import logging.config

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.cors import CORSMiddleware

from app.api.v1.wallets import router as wallets_router
from app.limiter import limiter
from app.logger.config import dict_config

logging.config.dictConfig(dict_config)
logger = logging.getLogger("wallet_api")

app = FastAPI(title="Wallet API")
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Обработчик превышения лимита запросов."""
    logger.warning("Превышен лимит запросов для %s", request.client.host)
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."},
    )


app.include_router(wallets_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("Приложение Wallet API запущено")
