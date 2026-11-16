from __future__ import annotations

import base64
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from . import storage
from .config import PIN_LENGTH, PIN_TTL_SECONDS

logger = logging.getLogger(__name__)


async def _get_avatar_data_url(bot: Bot, user_id: int) -> str | None:
    try:
        photos = await bot.get_user_profile_photos(user_id=user_id, limit=1)
        if not photos.photos:
            return None
        # smallest size of first photo
        photo = photos.photos[0][0]
        file = await bot.get_file(photo.file_id)
        if not file.file_path:
            return None
        buf = await bot.download_file(file.file_path)
        if buf is None:
            return None
        data = buf.read()
        if not data:
            return None
        # guess mime from path
        path = file.file_path.lower()
        if path.endswith(".png"):
            mime = "image/png"
        elif path.endswith(".webp"):
            mime = "image/webp"
        else:
            mime = "image/jpeg"
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception:
        logger.exception("Failed to fetch avatar for user_id=%s", user_id)
        return None


def create_dispatcher() -> Dispatcher:
    router = Router()

    @router.message(CommandStart())
    async def start_handler(message: Message, bot: Bot) -> None:
        tg_user = message.from_user
        if tg_user is None:
            await message.answer("Не удалось определить пользователя.")
            return

        avatar = await _get_avatar_data_url(bot, tg_user.id)
        user = storage.User(
            first_name=tg_user.first_name or "",
            last_name=tg_user.last_name,
            username=tg_user.username,
            avatar=avatar,
        )
        pin = storage.create_pin_for_user(user, ttl_seconds=PIN_TTL_SECONDS, length=PIN_LENGTH)
        await message.answer(
            f"Ваш PIN-код для входа: {pin}\n"
            f"Код действует {PIN_TTL_SECONDS // 60} минуты."
        )

    dp = Dispatcher()
    dp.include_router(router)
    return dp
