"""Duty selection service - shared logic for manual and automatic duty selection."""

from aiogram import Bot

from src.database.repositories import PoolRepository
from src.services.duty_manager import DutyManager
from src.services.notification import NotificationService
from src.utils.logger import setup_logging

logger = setup_logging(__name__)


async def select_and_announce_duty(
    session,
    bot: Bot,
    pool_id: int,
    group_id: int,
    is_automatic: bool = False,
) -> dict:
    """
    Select and announce duty for a pool.

    This function encapsulates the shared logic for both manual (/force_pick)
    and automatic (scheduler) duty selection.

    Args:
        session: Database session
        bot: Bot instance for sending notifications
        pool_id: Pool database ID
        group_id: Telegram group ID
        is_automatic: Whether this is an automatic selection (affects messaging)

    Returns:
        Dictionary with:
        - success: bool - Whether operation succeeded
        - message: str - Status message (for manual commands)
        - result: dict - Result from duty_manager
    """
    try:
        # Select duty
        duty_manager = DutyManager(session)
        result = await duty_manager.select_random_duty(pool_id)

        if not result:
            log_msg = "No users in pool" if is_automatic else "Failed to select duty"
            logger.warning(f"{log_msg} for pool {pool_id}")
            return {
                "success": False,
                "message": "❌ Не удалось выбрать дежурного. Возможно, в пуле нет участников.",
                "result": None,
            }

        # Check for error cases
        if result.get("error") == "all_pending":
            notification_service = NotificationService(bot, session)
            pending_duties = result.get("pending_duties", [])

            if not pending_duties:
                logger.info(f"All users have pending duties in pool {pool_id}, but list is empty")
                return {
                    "success": False,
                    "message": "ℹ️ Все участники пула уже получили предложение стать дежурными. Дождитесь ответов.",
                    "result": result,
                }

            if is_automatic:
                # For automatic selection, just skip and log
                logger.info(
                    f"Auto-selection: All users in pool {pool_id} have pending assignments, skipping"
                )
                return {
                    "success": True,
                    "message": "All users have pending duties, skipped",
                    "result": result,
                }
            else:
                # For manual selection, re-announce pending duties
                re_announced_count = 0
                for duty in pending_duties:
                    success = await notification_service.announce_duty_assignment(
                        group_id=group_id,
                        user_id=duty.user_id,
                        week_number=result["week_number"],
                        assignment_id=duty.id,
                        year=None,  # Use current year
                    )
                    if success:
                        re_announced_count += 1

                if re_announced_count > 0:
                    logger.info(
                        f"Re-announced {re_announced_count} pending duties in group {group_id}"
                    )
                    return {
                        "success": True,
                        "message": f"🔄 Напоминание отправлено {re_announced_count} участнику(-ам) с ожидающим подтверждением.",
                        "result": result,
                    }
                else:
                    return {
                        "success": False,
                        "message": "❌ Не удалось отправить напоминания.",
                        "result": result,
                    }

        if result.get("already_assigned"):
            log_prefix = "Auto-selection" if is_automatic else "Manual selection"
            logger.info(
                f"{log_prefix}: Duty already assigned for pool {pool_id}, week {result.get('week_number')}"
            )
            return {
                "success": True,
                "message": "ℹ️ Дежурный на неделю уже подтвержден.\nИспользуйте /duty чтобы посмотреть текущего дежурного.",
                "result": result,
            }

        # Announce new cycle if it was reset
        if result.get("cycle_reset"):
            notification_service = NotificationService(bot, session)
            await notification_service.announce_new_cycle(group_id)
            logger.info(f"New cycle started for pool {pool_id}")

        # Announce duty with confirmation buttons
        notification_service = NotificationService(bot, session)
        success = await notification_service.announce_duty_assignment(
            group_id=group_id,
            user_id=result["user_id"],
            week_number=result["week_number"],
            assignment_id=result["assignment_id"],
            is_automatic=is_automatic,
            year=None,  # Use current year
        )

        if success:
            log_prefix = "Auto-selected" if is_automatic else "Force picked"
            logger.info(
                f"✅ {log_prefix} duty: user {result['user_id']} "
                f"for week {result['week_number']} in group {group_id} (pool {pool_id})"
            )
            return {
                "success": True,
                "message": "✅ Дежурный успешно выбран и уведомлен.",
                "result": result,
            }
        else:
            logger.error(
                f"Failed to announce duty for pool {pool_id}: "
                f"user {result['user_id']}, week {result['week_number']}"
            )
            return {
                "success": False,
                "message": "❌ Ошибка при объявлении дежурного.",
                "result": result,
            }

    except Exception as e:
        logger.error(f"Error in select_and_announce_duty for pool {pool_id}: {e}", exc_info=True)
        return {
            "success": False,
            "message": "❌ Произошла ошибка при выборе дежурного.",
            "result": None,
        }
