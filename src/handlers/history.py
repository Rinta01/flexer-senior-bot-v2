"""History command handler - show duty history."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.config import settings
from src.database.engine import db_manager
from src.database.repositories import DutyRepository, PoolRepository
from src.utils.formatters import format_duty_status, format_user_display_name, get_week_dates
from src.utils.logger import setup_logging

logger = setup_logging(__name__)

router = Router()

# History limit (configurable via settings)
HISTORY_LIMIT = getattr(settings, "HISTORY_LIMIT", 10)


def format_duty_record(duty, index: int) -> str:
    """
    Format single duty record for history display.

    Args:
        duty: DutyAssignment object
        index: Record number (1-based)

    Returns:
        Formatted string for duty record
    """
    # Get week dates using centralized helper
    week_start, week_end = get_week_dates(duty.assignment_date.year, duty.week_number)
    date_range = f"{week_start.strftime('%d.%m')} - {week_end.strftime('%d.%m.%Y')}"

    # Format user using centralized helper
    user = duty.user
    user_name = format_user_display_name(user.first_name, user.username)

    # Status using centralized helper
    status_text = format_duty_status(duty.status)

    # Activity status
    has_activity = duty.activity_description or duty.activity_datetime
    activity_status = "📝 Мероприятие проведено" if has_activity else "📅 Без мероприятия"

    return (
        f"<b>{index}.</b> Неделя {duty.week_number}, {duty.assignment_date.year}\n"
        f"   📆 {date_range}\n"
        f"   👤 {user_name}\n"
        f"   {status_text}\n"
        f"   {activity_status}\n"
    )


@router.message(Command("history"))
async def history_command(message: Message) -> None:
    """Handle /history command - show recent duty history."""
    if not message.chat or message.chat.type == "private":
        await message.answer("❌ Эта команда работает только в группах.")
        return

    try:
        async with (
            db_manager.async_session() as session  # pyright: ignore[reportGeneralTypeIssues]
        ):
            pool_repo = PoolRepository(session)
            duty_repo = DutyRepository(session)

            # Get pool for this group
            pool = await pool_repo.get_by_id(message.chat.id)
            if not pool:
                await message.answer(
                    "❌ Пул дежурных для этой группы не найден.\n\n"
                    "Используйте /join чтобы создать пул и присоединиться!"
                )
                return

            logger.info(f"Fetching history for pool {pool.id} (limit: {HISTORY_LIMIT})")

            # Get recent duties
            duties = await duty_repo.get_recent_duties(pool.id, limit=HISTORY_LIMIT)

            if not duties:
                await message.answer(
                    "📜 <b>История дежурств</b>\n\n" "История пуста. Дежурные еще не назначались."
                )
                return

            # Format history message
            history_lines = [f"📜 <b>История дежурств (последние {len(duties)})</b>\n"]

            for i, duty in enumerate(duties, 1):
                history_lines.append(format_duty_record(duty, i))

            response = "\n".join(history_lines)
            await message.answer(response)
            logger.info(f"Sent history with {len(duties)} records")

    except Exception as e:
        logger.error(f"Error in history command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при получении истории.\n" "Попробуйте позже.")
