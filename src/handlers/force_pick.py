"""Force pick duty command handler."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.database.engine import db_manager
from src.database.repositories import PoolRepository, UserRepository, UserPoolRepository
from src.keyboards.week_selector import create_week_selector_keyboard
from src.utils.logger import setup_logging

logger = setup_logging(__name__)

router = Router()


@router.message(Command("force_pick"))
async def force_pick_command(message: Message) -> None:
    """
    Handle /force_pick command - manually assign duty to specific user for a week.

    Usage: /force_pick @username
    Example: /force_pick @john_doe
    """
    try:
        if not message.chat.id or message.chat.id > 0:
            await message.answer("⚠️ Эта команда работает только в групповых чатах!")
            return

        if not message.text:
            await message.answer("❌ Ошибка: текст команды отсутствует.")
            return

        # Parse username from command
        command_parts = message.text.split(maxsplit=1)
        if len(command_parts) < 2:
            await message.answer(
                "❌ Неверный формат команды.\n\n"
                "Использование: /force_pick @username\n"
                "Пример: /force_pick @john_doe"
            )
            return

        # Extract username (remove @ if present)
        username_arg = command_parts[1].strip()
        if username_arg.startswith("@"):
            username = username_arg[1:]
        else:
            username = username_arg

        if not username:
            await message.answer("❌ Укажите username пользователя после команды.")
            return

        async with db_manager.async_session() as session:
            # Get or create pool for this group
            pool_repo = PoolRepository(session)
            pool = await pool_repo.get_or_create(
                group_id=message.chat.id, group_title=message.chat.title or "Unknown Group"
            )

            # Find user by username
            user_repo = UserRepository(session)
            target_user = await user_repo.get_by_username(username)

            if not target_user:
                await message.answer(f"❌ Пользователь @{username} не найден в системе.")
                return

            # Check if user is in the pool
            user_pool_repo = UserPoolRepository(session)
            user_in_pool = await user_pool_repo.get_user_in_pool(pool.id, target_user.user_id)

            if not user_in_pool:
                await message.answer(
                    f"❌ Пользователь @{username} не состоит в пуле дежурных.\n"
                    f"Попросите пользователя выполнить /join"
                )
                return

            # Show week selection keyboard
            keyboard = create_week_selector_keyboard(
                action_prefix="force_pick_week", weeks_ahead=4, extra_data={"username": username}
            )

            await message.answer(
                f"📅 Выберите неделю для назначения дежурства пользователю @{username}:",
                reply_markup=keyboard,
            )

            logger.info(
                f"Force pick initiated for user @{username} (ID {target_user.user_id}) "
                f"in group {message.chat.id} (pool {pool.id})"
            )

    except Exception as e:
        logger.error(f"Error in force_pick_command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обработке команды.")

    except Exception as e:
        logger.error(f"Error in force_pick_command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при назначении дежурного.")
