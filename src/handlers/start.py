"""Start command handler."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.utils.logger import setup_logging

logger = setup_logging(__name__)

router = Router()


@router.message(Command("start"))
async def start_command(message: Message) -> None:
    """Handle /start command."""
    try:
        welcome_text = (
            "👋 Добро пожаловать в Флексер старший!\n\n"
            "Я помогу организовать ротацию дежурных в группе. 🎯\n\n"
            "<b>Основные команды:</b>\n"
            "/join - присоединиться к пулу дежурных\n"
            "/leave - выйти из пула дежурных\n"
            "/duty - узнать текущего дежурного\n"
            "/help - полная справка\n\n"
            "Давайте начнём! 💪"
        )

        await message.answer(welcome_text, parse_mode="HTML")
        logger.info(f"Handled /start from user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте позже.")
