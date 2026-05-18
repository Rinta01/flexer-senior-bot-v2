"""Tests for calendar link utilities."""

from datetime import datetime
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from src.database.models import TelegramUser
from src.utils.calendar import (
    build_activity_description_for_storage,
    build_google_calendar_url,
    escape_ics_text,
    extract_location_from_description,
)


def test_escape_ics_text_escapes_special_characters():
    """Test iCalendar text escaping."""
    assert escape_ics_text("A, B; C\\D\nE") == "A\\, B\\; C\\\\D\\nE"


def test_build_google_calendar_url_uses_activity_details():
    """Test Google Calendar URL contains prefilled activity fields."""
    user = TelegramUser(user_id=123, first_name="Rinat", username="rinta")
    url = build_google_calendar_url(
        title="Лазертаг",
        description="Берите удобную одежду",
        activity_datetime=datetime(2026, 5, 25, 18, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        location="Арена",
        user=user,
    )
    query = parse_qs(urlparse(url).query)

    assert query["action"] == ["TEMPLATE"]
    assert query["text"] == ["Лазертаг"]
    assert query["dates"] == ["20260525T150000Z/20260525T180000Z"]
    assert query["location"] == ["Арена"]
    assert "Берите удобную одежду" in query["details"][0]
    assert "Дежурный: Rinat (@rinta)" in query["details"][0]


def test_activity_description_storage_round_trip():
    """Test storing location in activity_description remains recoverable."""
    stored = build_activity_description_for_storage("Описание", "Арена")

    assert stored == "Описание\nМесто: Арена"
    assert extract_location_from_description(stored) == ("Описание", "Арена")
