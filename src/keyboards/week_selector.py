"""Week selector keyboard for duty assignment."""

from datetime import datetime, timedelta
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_week_start_end(year: int, week: int) -> tuple[datetime, datetime]:
    """
    Get start (Monday) and end (Sunday) dates for a given week number.

    Args:
        year: Year number
        week: ISO week number (1-53)

    Returns:
        Tuple of (start_date, end_date) for the week
    """
    # Get the first day of the year
    jan_first = datetime(year, 1, 1)

    # Find the first Monday of the ISO year
    # ISO weeks start on Monday
    days_to_monday = (7 - jan_first.weekday()) % 7
    if jan_first.weekday() > 3:  # If Jan 1 is Thu-Sun, week 1 starts next Monday
        days_to_monday += 7

    # Calculate the start of the requested week
    first_monday = jan_first + timedelta(days=days_to_monday)
    week_start = first_monday + timedelta(weeks=week - 1)
    week_end = week_start + timedelta(days=6)

    return week_start, week_end


def format_week_display(week_number: int, year: int | None = None) -> str:
    """
    Format week number for display with date range.

    Args:
        week_number: ISO week number
        year: Year (defaults to current year)

    Returns:
        Formatted string like "Неделя 42 (14.10 - 20.10)"
    """
    if year is None:
        year = datetime.now().year

    start, end = get_week_start_end(year, week_number)

    return f"Неделя {week_number} ({start.strftime('%d.%m')} - {end.strftime('%d.%m')})"


def create_week_selector_keyboard(
    action_prefix: str,
    weeks_ahead: int = 4,
    extra_data: dict[str, Any] | None = None,
) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for week selection.

    Args:
        action_prefix: Prefix for callback data (e.g., "pick_week" or "force_pick_week")
        weeks_ahead: Number of weeks ahead to show (default: 4)
        extra_data: Additional data to include in callback (e.g., {"username": "john"})

    Returns:
        InlineKeyboardMarkup with week selection buttons
    """
    builder = InlineKeyboardBuilder()

    current_date = datetime.now()
    current_year = current_date.year
    current_week = current_date.isocalendar()[1]

    # Create buttons for current week + next N weeks
    for i in range(weeks_ahead + 1):
        week_num = current_week + i
        year = current_year

        # Handle year rollover
        if week_num > 52:
            week_num = week_num - 52
            year = current_year + 1

        # Create callback data
        callback_parts = [action_prefix, str(year), str(week_num)]

        # Add extra data if provided
        if extra_data:
            for key, value in extra_data.items():
                callback_parts.append(f"{key}:{value}")

        callback_data = ":".join(callback_parts)

        # Format button text
        button_text = format_week_display(week_num, year)
        if i == 0:
            button_text = f"📍 {button_text} (текущая)"

        builder.button(text=button_text, callback_data=callback_data)

    # One button per row for better readability
    builder.adjust(1)

    return builder.as_markup()


def parse_week_callback(callback_data: str) -> dict[str, Any]:
    """
    Parse callback data from week selector.

    Args:
        callback_data: Callback data string (e.g., "pick_week:2026:5" or "force_pick_week:2026:5:username:john")

    Returns:
        Dictionary with parsed data: {"action": str, "year": int, "week": int, ...extra}
    """
    parts = callback_data.split(":")

    if len(parts) < 3:
        raise ValueError(f"Invalid callback data format: {callback_data}")

    result = {
        "action": parts[0],
        "year": int(parts[1]),
        "week": int(parts[2]),
    }

    # Parse extra data (key:value pairs)
    for i in range(3, len(parts), 2):
        if i + 1 < len(parts):
            result[parts[i]] = parts[i + 1]

    return result
