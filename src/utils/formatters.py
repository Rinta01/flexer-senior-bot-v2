"""Formatting utilities for messages and dates."""

from datetime import datetime, timedelta

from src.config import settings


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

    # Get Monday of the week
    jan_4 = datetime(year, 1, 4)  # Week 1 always contains Jan 4
    week_1_monday = jan_4 - timedelta(days=jan_4.weekday())
    target_monday = week_1_monday + timedelta(weeks=week_number - 1)
    target_sunday = target_monday + timedelta(days=6)

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
