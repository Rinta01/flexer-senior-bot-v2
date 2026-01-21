"""Pick duty command handler - random duty selection with week choice."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.database.engine import db_manager
from src.database.repositories import PoolRepository, UserPoolRepository
from src.keyboards.week_selector import create_week_selector_keyboard
from src.utils.logger import setup_logging

logger = setup_logging(__name__)

router = Router()


@router.message(Command("pick"))
async def pick_command(message: Message) -> None:
    """
    Handle /pick command - randomly select duty for a specific week.

    Shows week selection keyboard, then randomly picks user from pool.
    """
    try:
        if not message.chat.id or message.chat.id > 0:
            await message.answer("⚠️ Эта команда работает только в групповых чатах!")
            return

        async with db_manager.async_session() as session:
            # Get or create pool for this group
            pool_repo = PoolRepository(session)
            pool = await pool_repo.get_or_create(
                group_id=message.chat.id, group_title=message.chat.title or "Unknown Group"
            )

            # Check if pool has users
            user_pool_repo = UserPoolRepository(session)
            users_in_pool = await user_pool_repo.get_active_users(pool.id)

            if not users_in_pool:
                await message.answer(
                    "❌ В пуле дежурных пока нет участников.\n\n"
                    "Используйте /join чтобы присоединиться."
                )
                return

            # Show week selection keyboard
            keyboard = create_week_selector_keyboard(action_prefix="pick_week", weeks_ahead=4)

            await message.answer(
                f"📅 Выберите неделю для случайного выбора дежурного:\n\n"
                f"В пуле дежурных: {len(users_in_pool)} участников",
                reply_markup=keyboard,
            )

            logger.info(
                f"Pick command initiated in group {message.chat.id} (pool {pool.id}), "
                f"{len(users_in_pool)} users in pool"
            )

    except Exception as e:
        logger.error(f"Error in pick_command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обработке команды.")
