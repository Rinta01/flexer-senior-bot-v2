"""Utilities for generating calendar files."""

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from src.database.models import DutyAssignment, TelegramUser
from src.utils.formatters import get_week_dates

CHAT_TIMEZONE = timezone(timedelta(hours=3), "UTC+03:00")


def escape_ics_text(value: str) -> str:
    """Escape text according to iCalendar text value rules."""
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def fold_ics_line(line: str, limit: int = 75) -> str:
    """Fold a long iCalendar line."""
    if len(line) <= limit:
        return line

    parts = [line[:limit]]
    remaining = line[limit:]
    while remaining:
        parts.append(f" {remaining[: limit - 1]}")
        remaining = remaining[limit - 1 :]
    return "\r\n".join(parts)


def build_google_calendar_url(
    title: str,
    description: str | None = None,
    activity_datetime: datetime | None = None,
    location: str | None = None,
    user: TelegramUser | None = None,
    duty: DutyAssignment | None = None,
) -> str:
    """Build Google Calendar prefill URL for an activity."""
    params = {
        "action": "TEMPLATE",
        "text": title.strip() if title and title.strip() else "Активность недели",
    }

    if activity_datetime:
        starts_at = activity_datetime
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=CHAT_TIMEZONE)
        ends_at = starts_at + timedelta(hours=3)
        params["dates"] = (
            f"{starts_at.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}/"
            f"{ends_at.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        )
    elif duty:
        iso_year = duty.assignment_date.isocalendar()[0]
        week_start, week_end = get_week_dates(iso_year, duty.week_number)
        params["dates"] = (
            f"{week_start.strftime('%Y%m%d')}/"
            f"{(week_end + timedelta(days=1)).strftime('%Y%m%d')}"
        )

    details_parts = []
    if description and description.strip():
        details_parts.append(description.strip())
    if user:
        duty_person = user.first_name
        if user.username:
            duty_person = f"{duty_person} (@{user.username})"
        details_parts.append(f"Дежурный: {duty_person}")
    if details_parts:
        params["details"] = "\n".join(details_parts)

    if location and location.strip():
        params["location"] = location.strip()

    return "https://calendar.google.com/calendar/render?" + urlencode(params)


def extract_location_from_description(description: str | None) -> tuple[str, str]:
    """Extract optional location from a stored activity description."""
    if not description:
        return "", ""

    location = ""
    clean_lines = []
    location_pattern = re.compile(
        r"^(?:место(?:\s+проведения)?|локация|где(?:\s+встречаемся)?|адрес)(?:\s*[:\-–—]\s*|\s+)(.+)$",
        re.I,
    )

    for line in description.splitlines():
        match = location_pattern.match(line.strip())
        if match and not location:
            location = match.group(1).strip()
        else:
            clean_lines.append(line)

    return "\n".join(clean_lines).strip(), location


def build_activity_description_for_storage(description: str, location: str) -> str | None:
    """Store description and location in one existing DB field."""
    parts = []
    if description.strip():
        parts.append(description.strip())
    if location.strip():
        parts.append(f"Место: {location.strip()}")
    return "\n".join(parts) if parts else None
