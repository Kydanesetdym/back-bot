from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from . import storage
from .bot import create_dispatcher
from .config import (
    AUTH_MAX_FAILURES,
    AUTH_WINDOW_SECONDS,
    BASE_URL,
    BOT_TOKEN,
    BOT_USERNAME,
    SERVER_HOST,
    SERVER_PORT,
    WEBHOOK_PATH,
    WEBHOOK_SECRET,
)
from .ratelimit import FailureLimiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = create_dispatcher()
runtime_bot_username: str = BOT_USERNAME
auth_limiter = FailureLimiter(AUTH_MAX_FAILURES, AUTH_WINDOW_SECONDS)


class AuthRequest(BaseModel):
    key: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global runtime_bot_username
    if bot:
        try:
            me = await bot.get_me()
            if me.username:
                runtime_bot_username = me.username
                logger.info("Bot username: @%s", runtime_bot_username)
        except Exception:
            logger.exception("Failed to fetch bot info")

    if bot and BASE_URL:
        webhook_url = f"{BASE_URL}{WEBHOOK_PATH}"
        try:
            await bot.set_webhook(
    webhook_url,
    secret_token=WEBHOOK_SECRET,
    drop_pending_updates=True,
)
            logger.info("Webhook set: %s", webhook_url)
        except Exception:
            logger.exception("Failed to set webhook to %s", webhook_url)
    elif bot and not BASE_URL:
        logger.warning("BASE_URL is not set; webhook was not configured. Set BASE_URL to your ngrok https URL.")
    else:
        logger.warning("BOT_TOKEN is not set; bot/webhook not initialized.")
    yield
    if bot:
        try:
            if BASE_URL:
                await bot.delete_webhook(drop_pending_updates=False)
        except Exception:
            logger.exception("Failed to delete webhook")
        await bot.session.close()


app = FastAPI(title="BE Task01 Server", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/auth")
async def auth(payload: AuthRequest, request: Request):
    ip = request.client.host if request.client else "unknown"

    wait = auth_limiter.retry_after(ip)
    if wait:
        raise HTTPException(
            status_code=429,
            detail=f"Слишком много попыток. Повторите через {wait} с.",
            headers={"Retry-After": str(wait)},
        )

    user = storage.consume_pin(payload.key)
    if not user:
        auth_limiter.register_failure(ip)
        raise HTTPException(status_code=401, detail="Неверный или истёкший PIN-код")

    auth_limiter.reset(ip)
    return user.to_dict()


@app.get("/bot")
async def bot_info():
    username = runtime_bot_username
    if not username:
        raise HTTPException(status_code=404, detail="Bot username is not configured")
    return {"username": username, "url": f"https://t.me/{username}"}


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    received = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not secrets.compare_digest(received, WEBHOOK_SECRET):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not bot:
        raise HTTPException(status_code=503, detail="Bot is not configured")
    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}


def run() -> None:
    import uvicorn

    uvicorn.run("server.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)


if __name__ == "__main__":
    run()
