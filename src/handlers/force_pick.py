"""Force pick duty command handler."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.database.engine import db_manager
from src.database.repositories import PoolRepository
from src.services.duty_selector import select_and_announce_duty
from src.utils.logger import setup_logging

logger = setup_logging(__name__)

router = Router()


@router.message(Command("force_pick"))
async def force_pick_command(message: Message) -> None:
    """Handle /force_pick command - manually select duty."""
    try:
        if not message.chat.id or message.chat.id > 0:
            await message.answer("⚠️ Эта команда работает только в групповых чатах!")
            return

        if not message.bot:
            await message.answer("❌ Ошибка: бот недоступен.")
            return

        async with db_manager.async_session() as session:
            # Get or create pool for this group
            pool_repo = PoolRepository(session)
            pool = await pool_repo.get_or_create(
                group_id=message.chat.id, group_title=message.chat.title or "Unknown Group"
            )

            # Use shared duty selection logic
            result = await select_and_announce_duty(
                session=session,
                bot=message.bot,
                pool_id=pool.id,
                group_id=message.chat.id,
                is_automatic=False,
            )

            # Send response message
            if result["message"]:
                await message.answer(result["message"])

    except Exception as e:
        logger.error(f"Error in force_pick_command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при выборе дежурного.")
