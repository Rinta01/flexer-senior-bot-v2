"""Duty-related command handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.database.engine import db_manager
from src.database.repositories import PoolRepository, UserRepository
from src.services.duty_manager import DutyManager
from src.utils.formatters import get_schedule_description
from src.utils.logger import setup_logging
from src.utils.validators import format_user_mention

logger = setup_logging(__name__)

router = Router()


@router.message(Command("duty"))
async def duty_command(message: Message) -> None:
    """Handle /duty command - show current duty."""
    try:
        if not message.chat.id or message.chat.id > 0:
            await message.answer("⚠️ Эта команда работает только в групповых чатах!")
            return

        async with db_manager.async_session() as session:
            duty_manager = DutyManager(session)
            user_repo = UserRepository(session)

            # Get current duty
            current_duty = await duty_manager.get_current_duty(message.chat.id)

            if not current_duty:
                await message.answer("ℹ️ На эту неделю дежурный ещё не выбран.")
                return

            # Get user info
            user = await user_repo.get_by_id(current_duty["user_id"])
            if not user:
                await message.answer("❌ Не удалось найти информацию о дежурном.")
                return

            mention = format_user_mention(current_duty["user_id"], user.username)
            response = (
                f"🎯 <b>Текущий дежурный</b>\n\n"
                f"Неделя #{current_duty['week_number']}\n"
                f"Дежурный: {mention}\n\n"
                f"Спасибо за организацию мероприятия! 🙏"
            )

            await message.answer(response, parse_mode="HTML")
            logger.info(f"Handled /duty in group {message.chat.id}")

    except Exception as e:
        logger.error(f"Error in duty_command: {e}")
        await message.answer("❌ Произошла ошибка при получении информации о дежурном.")


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    """Handle /help command - show help."""
    schedule = get_schedule_description()
    help_text = (
        "<b>📚 Справка по командам</b>\n\n"
        "<b>/join</b> - Присоединиться к пулу дежурных\n"
        "После этого вы будете участвовать в ротации.\n\n"
        "<b>/leave</b> - Выйти из пула дежурных\n"
        "Вас больше не будут выбирать дежурным.\n\n"
        "<b>/duty</b> - Показать текущего дежурного\n"
        "Узнайте, кто дежурит на этой неделе.\n\n"
        "<b>ℹ️ Как это работает</b>\n"
        f"• {schedule.capitalize()} бот выбирает одного дежурного\n"
        "• Дежурного выбирают случайно из активных участников\n"
        "• Дежурный не повторяется, пока все не побывают\n"
        "• После завершения цикла начинается новый раунд\n\n"
        "Удачи! 💪"
    )

    await message.answer(help_text, parse_mode="HTML")
