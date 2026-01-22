"""Formatting utilities for messages and dates."""

from datetime import datetime, timedelta

from src.config import settings
from src.database.models import DutyStatus
from src.utils.validators import validate_username


def get_schedule_description() -> str:
    """Get schedule description from settings.

    Returns:
        Formatted schedule description like "каждый понедельник в 10:00 UTC"
    """
    weekdays = [
        "понедельник",
        "вторник",
        "среду",
        "четверг",
        "пятницу",
        "субботу",
        "воскресенье",
    ]
    day_name = weekdays[settings.WEEKLY_DUTY_DAY % 7]
    return f"раз в неделю в {day_name} в {settings.WEEKLY_DUTY_HOUR:02d}:{settings.WEEKLY_DUTY_MINUTE:02d} МСК"


def get_week_dates(year: int, week: int) -> tuple[datetime, datetime]:
    """
    Calculate start (Monday) and end (Sunday) dates for ISO week.

    This is the canonical implementation used across the codebase.

    Args:
        year: Year
        week: ISO week number (1-53)

    Returns:
        Tuple of (start_date, end_date) for the week
    """
    # ISO week 1 is the week containing January 4th
    jan_4 = datetime(year, 1, 4)
    week_1_start = jan_4 - timedelta(days=jan_4.weekday())
    week_start = week_1_start + timedelta(weeks=week - 1)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def get_week_date_range(week_number: int, year: int | None = None) -> str:
    """Format week date range for display.

    Args:
        week_number: ISO week number
        year: Year (defaults to current year)

    Returns:
        Formatted date range string like "13 января - 19 января"
    """
    if year is None:
        year = datetime.now().year

    target_monday, target_sunday = get_week_dates(year, week_number)

    months_ru = [
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ]

    monday_str = f"{target_monday.day} {months_ru[target_monday.month - 1]}"
    sunday_str = f"{target_sunday.day} {months_ru[target_sunday.month - 1]}"

    return f"{monday_str} - {sunday_str}"


def format_duty_status(status: DutyStatus) -> str:
    """
    Format duty status with emoji.

    Args:
        status: DutyStatus enum value

    Returns:
        Formatted status string with emoji
    """
    status_map = {
        DutyStatus.PENDING: "⏳ Ожидает подтверждения",
        DutyStatus.CONFIRMED: "✅ Подтверждено",
        DutyStatus.DECLINED: "❌ Отказался",
        DutyStatus.SKIPPED: "⏭️ Пропущено",
    }
    return status_map.get(status, str(status.value))


def format_user_display_name(first_name: str, username: str | None = None) -> str:
    """
    Format user display name with username if available.

    Args:
        first_name: User's first name
        username: User's Telegram username (optional)

    Returns:
        Formatted display name like "Иван (@ivan_petrov)" or "Иван"
    """
    if username:
        return f"{first_name} (@{username})"
    return first_name


def format_user_mention(
    user_id: int, username: str | None = None, first_name: str | None = None
) -> str:
    """
    Format user mention for Telegram message.

    Args:
        user_id: Telegram user ID
        username: Telegram username (if available)
        first_name: User's first name (used as fallback)

    Returns:
        Formatted mention string
    """
    if username and validate_username(username):
        return f"@{username}"

    # Use first_name for display in clickable mention if available
    display_name = first_name or f"User {user_id}"
    return f"[{display_name}](tg://user?id={user_id})"
