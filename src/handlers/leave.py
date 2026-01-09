"""Leave command handler."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.database.engine import db_manager
from src.services.user_manager import UserManager
from src.utils.logger import setup_logging

logger = setup_logging(__name__)

router = Router()


@router.message(Command("leave"))
async def leave_command(message: Message) -> None:
    """Handle /leave command - remove user from duty pool."""
    try:
        if not message.chat.id or message.chat.id > 0:
            # Private chat or channel
            await message.answer("⚠️ Эта команда работает только в групповых чатах!")
            return

        # Get database session
        async with db_manager.async_session() as session:
            user_manager = UserManager(session)

            # Remove user from pool
            success, response_text = await user_manager.remove_user_from_pool(
                user_id=message.from_user.id,
                pool_id=message.chat.id,
            )

            if success:
                # Get updated pool count
                count = await user_manager.get_pool_users_count(message.chat.id)
                response_text += f"\n\n👥 Участников в пуле: {count}"

            await message.answer(response_text)
            logger.info(f"User {message.from_user.id} left pool in {message.chat.id}")

    except Exception as e:
        logger.error(f"Error in leave_command: {e}")
        await message.answer("❌ Произошла ошибка при удалении из пула.")
