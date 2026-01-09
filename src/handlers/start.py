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
            "/pool - список всех участников пула\n"
            "/duty - узнать текущего дежурного\n"
            "/force_pick - выбрать дежурного вручную\n"
            "/help - полная справка\n\n"
            "Давайте начнём! 💪"
        )

        await message.answer(welcome_text, parse_mode="HTML")
        user_id = message.from_user.id if message.from_user else "unknown"
        logger.info(f"Handled /start from user {user_id}")

    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте позже.")


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    """Handle /help command."""
    try:
        help_text = (
            "📖 <b>Справка по Флексеру старшему</b>\n\n"
            "<b>Команды:</b>\n\n"
            "/start - показать приветствие\n"
            "/join - присоединиться к пулу дежурных\n"
            "/leave - выйти из пула дежурных\n"
            "/pool - показать список всех участников\n"
            "/duty - показать текущего дежурного\n"
            "/force_pick - выбрать дежурного вручную (в обход расписания)\n"
            "/help - показать эту справку\n\n"
            "<b>Как это работает:</b>\n"
            "1️⃣ Участники присоединяются через /join\n"
            "2️⃣ Бот автоматически выбирает дежурного каждую неделю\n"
            "3️⃣ Дежурный должен подтвердить или отказаться\n"
            "4️⃣ Никто не повторяется, пока все не побывают дежурными\n"
            "5️⃣ После полного цикла ротация начинается заново\n\n"
            "Для работы добавьте бота в группу! 🤖"
        )

        await message.answer(help_text, parse_mode="HTML")
        user_id = message.from_user.id if message.from_user else "unknown"
        logger.info(f"Handled /help from user {user_id}")

    except Exception as e:
        logger.error(f"Error in help_command: {e}")
        await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте позже.")
