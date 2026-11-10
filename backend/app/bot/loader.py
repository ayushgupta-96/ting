from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from app.core.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

bot: Optional[Bot] = None
dp = Dispatcher()

if settings.BOT_TOKEN:
    try:
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
    except Exception as e:
        logger.warning(f"Telegram Bot could not be initialized with current token: {e}")
        bot = None
