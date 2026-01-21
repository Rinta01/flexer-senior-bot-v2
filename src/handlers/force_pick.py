"""Force pick duty command handler."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.database.engine import db_manager
from src.database.repositories import PoolRepository, UserRepository, UserPoolRepository
from src.services.duty_manager import DutyManager
from src.services.notification import NotificationService
from src.utils.logger import setup_logging

logger = setup_logging(__name__)

router = Router()


@router.message(Command("force_pick"))
async def force_pick_command(message: Message) -> None:
    """
    Handle /force_pick command - manually assign duty to specific user.

    Usage: /force_pick @username
    Example: /force_pick @john_doe
    """
    try:
        if not message.chat.id or message.chat.id > 0:
            await message.answer("⚠️ Эта команда работает только в групповых чатах!")
            return

        if not message.bot or not message.text:
            await message.answer("❌ Ошибка: бот недоступен.")
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

            # Find user by username in the pool
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

            # Assign duty to specific user
            duty_manager = DutyManager(session)
            result = await duty_manager.assign_duty_to_user(pool.id, target_user.user_id)

            if not result:
                await message.answer(
                    f"❌ Не удалось назначить @{username} дежурным.\n"
                    f"Возможно, на этой неделе уже есть подтвержденный дежурный."
                )
                return

            # Announce duty with confirmation buttons
            notification_service = NotificationService(message.bot, session)
            success = await notification_service.announce_duty_assignment(
                group_id=message.chat.id,
                user_id=target_user.user_id,
                week_number=result["week_number"],
                assignment_id=result["assignment_id"],
                is_automatic=False,
            )

            if success:
                logger.info(
                    f"✅ Force picked duty: user @{username} (ID {target_user.user_id}) "
                    f"for week {result['week_number']} in group {message.chat.id} (pool {pool.id})"
                )
                await message.answer(
                    f"✅ Уведомление отправлено пользователю @{username}.\n"
                    f"Ожидается подтверждение дежурства на неделю {result['week_number']}."
                )
            else:
                logger.error(f"Failed to announce duty for user @{username}")
                await message.answer("❌ Ошибка при объявлении дежурного.")

    except Exception as e:
        logger.error(f"Error in force_pick_command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при назначении дежурного.")
