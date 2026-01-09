"""Force pick duty command handler."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.database.engine import db_manager
from src.database.repositories import PoolRepository
from src.services.duty_manager import DutyManager
from src.services.notification import NotificationService
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

        async with db_manager.async_session() as session:
            # Get or create pool for this group
            pool_repo = PoolRepository(session)
            pool = await pool_repo.get_or_create(
                group_id=message.chat.id, group_title=message.chat.title or "Unknown Group"
            )

            # Select duty
            duty_manager = DutyManager(session)
            result = await duty_manager.select_random_duty(pool.id)

            if not result:
                await message.answer(
                    "❌ Не удалось выбрать дежурного. Возможно, в пуле нет участников."
                )
                return

            # Check for error cases
            if result.get("error") == "all_pending":
                # Re-announce all pending duties
                bot = message.bot
                if not bot:
                    await message.answer("❌ Ошибка: бот недоступен.")
                    return

                notification_service = NotificationService(bot, session)
                pending_duties = result.get("pending_duties", [])

                if not pending_duties:
                    await message.answer(
                        "ℹ️ Все участники пула уже получили предложение стать дежурными. "
                        "Дождитесь ответов."
                    )
                    return

                # Re-send notifications for all pending duties
                re_announced_count = 0
                for duty in pending_duties:
                    success = await notification_service.announce_duty_assignment(
                        group_id=message.chat.id,
                        user_id=duty.user_id,
                        week_number=result["week_number"],
                        assignment_id=duty.id,
                    )
                    if success:
                        re_announced_count += 1

                if re_announced_count > 0:
                    await message.answer(
                        f"🔄 Напоминание отправлено {re_announced_count} участнику(-ам) "
                        f"с ожидающим подтверждением."
                    )
                    logger.info(
                        f"Re-announced {re_announced_count} pending duties in group {message.chat.id}"
                    )
                else:
                    await message.answer("❌ Не удалось отправить напоминания.")
                return

            if result.get("already_assigned"):
                await message.answer(
                    f"ℹ️ Дежурный на неделю уже подтвержден.\n"
                    f"Используйте /duty чтобы посмотреть текущего дежурного."
                )
                return

            # Announce duty with confirmation buttons
            bot = message.bot
            if not bot:
                await message.answer("❌ Ошибка: бот недоступен.")
                return
            notification_service = NotificationService(bot, session)

            success = await notification_service.announce_duty_assignment(
                group_id=message.chat.id,
                user_id=result["user_id"],
                week_number=result["week_number"],
                assignment_id=result["assignment_id"],
            )

            if success:
                logger.info(
                    f"Force picked duty: user {result['user_id']} for week {result['week_number']} "
                    f"in group {message.chat.id}"
                )
            else:
                await message.answer("❌ Ошибка при объявлении дежурного.")

    except Exception as e:
        logger.error(f"Error in force_pick_command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при выборе дежурного.")
