"""Start command handler."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.utils.formatters import get_schedule_description
from src.utils.logger import setup_logging

logger = setup_logging(__name__)

router = Router()


@router.message(Command("start"))
async def start_command(message: Message) -> None:
    """Handle /start command."""
    try:
        # schedule = get_schedule_description()
        welcome_text = (
            "👋 Здарова, машины! Я Флексер старший!\n\n"
            "Я помогу вам сохранить дружбу и жить разнообразно 🎯\n\n"
            "<b>Основные команды:</b>\n"
            "/join - присоединиться к пулу дежурных\n"
            "/leave - выйти из пула дежурных\n"
            "/pool - список всех участников пула\n"
            "/activity - дежурный и активность недели\n"
            "/set_activity - установить активность\n"
            "/help - полная справка\n\n"
            # f"⏰ <b>Автовыбор дежурного:</b> {schedule}\n\n"
        )

        await message.answer(welcome_text, parse_mode="HTML")
        user_id = message.from_user.id if message.from_user else "unknown"
        logger.info(f"Handled /start from user {user_id}")

    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте позже.")
