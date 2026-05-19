"""Tests for scheduler target week calculation."""

from datetime import datetime

from src.bot import SCHEDULER_TIMEZONE, get_next_week_for_scheduler


def test_scheduler_targets_next_week_when_run_on_tuesday():
    """Scheduler should always target the next ISO week, not the current week."""
    now = datetime(2026, 5, 19, 15, 0, tzinfo=SCHEDULER_TIMEZONE)

    assert now.isocalendar().week == 21
    assert get_next_week_for_scheduler(now) == (2026, 22)


def test_scheduler_targets_next_week_across_year_boundary():
    """Scheduler target week calculation should handle ISO year rollover."""
    now = datetime(2026, 12, 29, 15, 0, tzinfo=SCHEDULER_TIMEZONE)

    assert get_next_week_for_scheduler(now) == (2027, 1)
