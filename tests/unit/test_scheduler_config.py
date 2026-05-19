"""Tests for scheduler configuration."""

from datetime import time

import pytest

from src.config import Settings


def test_weekly_duty_defaults_to_sunday_15_utc3():
    """Scheduler defaults should match the production UX expectation."""
    settings = Settings(_env_file=None)

    assert settings.WEEKLY_DUTY_ENABLED is True
    assert settings.get_weekly_duty_day() == 6
    assert settings.get_weekly_duty_time() == time(hour=15, minute=0)


def test_weekly_duty_time_can_be_configured():
    """Scheduler time should be configurable with HH:MM env-style value."""
    settings = Settings(WEEKLY_DUTY_TIME="09:45", _env_file=None)

    assert settings.get_weekly_duty_time() == time(hour=9, minute=45)


def test_weekly_duty_day_can_be_configured():
    """Scheduler weekday should be configurable with 0..6 values."""
    settings = Settings(WEEKLY_DUTY_DAY=0, _env_file=None)

    assert settings.get_weekly_duty_day() == 0


def test_weekly_duty_day_rejects_invalid_value():
    """Invalid weekday values should fail loudly during scheduler setup."""
    settings = Settings(WEEKLY_DUTY_DAY=7, _env_file=None)

    with pytest.raises(ValueError, match="WEEKLY_DUTY_DAY"):
        settings.get_weekly_duty_day()


def test_weekly_duty_time_rejects_invalid_value():
    """Invalid time values should fail loudly during scheduler setup."""
    settings = Settings(WEEKLY_DUTY_TIME="25:00", _env_file=None)

    with pytest.raises(ValueError, match="WEEKLY_DUTY_TIME"):
        settings.get_weekly_duty_time()
