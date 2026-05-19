"""Tests for shared duty selection orchestration."""

from unittest.mock import AsyncMock, patch

import pytest

from src.services.duty_selector import select_and_announce_duty


@pytest.mark.asyncio
async def test_select_and_announce_duty_can_target_specific_week():
    """Automatic scheduler should be able to select duty for the next week."""
    session = AsyncMock()
    bot = AsyncMock()

    result = {
        "user_id": 123456789,
        "week_number": 22,
        "year": 2026,
        "assignment_id": 42,
        "already_assigned": False,
    }

    with (
        patch("src.services.duty_selector.DutyManager") as duty_manager_class,
        patch("src.services.duty_selector.NotificationService") as notification_class,
    ):
        duty_manager = AsyncMock()
        duty_manager.select_random_duty_for_week.return_value = result
        duty_manager_class.return_value = duty_manager

        notification = AsyncMock()
        notification.announce_duty_assignment.return_value = True
        notification_class.return_value = notification

        response = await select_and_announce_duty(
            session=session,
            bot=bot,
            pool_id=1,
            group_id=-100,
            is_automatic=True,
            year=2026,
            week_number=22,
        )

    assert response["success"] is True
    duty_manager.select_random_duty_for_week.assert_awaited_once_with(1, 2026, 22)
    duty_manager.select_random_duty.assert_not_called()
    notification.announce_duty_assignment.assert_awaited_once_with(
        group_id=-100,
        user_id=123456789,
        week_number=22,
        assignment_id=42,
        is_automatic=True,
        year=2026,
    )
