"""Unit tests for DutyManager."""

import pytest
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DutyPool, TelegramUser, UserInPool
from src.services.duty_manager import DutyManager


@pytest.mark.asyncio
async def test_select_random_duty_no_users(db_session: AsyncSession):
    """Test duty selection with no users in pool."""
    # Create pool
    pool = DutyPool(group_id=-123, group_title="Test Group")
    db_session.add(pool)
    await db_session.commit()

    # Try to select duty
    duty_manager = DutyManager(db_session)
    result = await duty_manager.select_random_duty(pool.id)

    assert result is None


@pytest.mark.asyncio
async def test_select_random_duty_single_user(
    db_session: AsyncSession,
    sample_user_data: dict,
    sample_group_data: dict,
):
    """Test duty selection with single user in pool."""
    # Create user
    user = TelegramUser(**sample_user_data)
    db_session.add(user)
    await db_session.flush()

    # Create pool
    pool = DutyPool(**sample_group_data)
    db_session.add(pool)
    await db_session.flush()

    # Add user to pool
    user_in_pool = UserInPool(user_id=user.user_id, pool_id=pool.id)
    db_session.add(user_in_pool)
    await db_session.commit()

    # Select duty
    duty_manager = DutyManager(db_session)
    result = await duty_manager.select_random_duty(pool.id)

    assert result is not None
    assert result["user_id"] == sample_user_data["user_id"]
    assert result["already_assigned"] is False


@pytest.mark.asyncio
async def test_duty_not_repeated_in_cycle(
    db_session: AsyncSession,
    sample_group_data: dict,
):
    """Test that duty doesn't repeat until cycle completes."""
    # Create pool
    pool = DutyPool(**sample_group_data)
    db_session.add(pool)
    await db_session.flush()

    # Create 2 users
    user1 = TelegramUser(user_id=111, first_name="User1", username="user1")
    user2 = TelegramUser(user_id=222, first_name="User2", username="user2")
    db_session.add_all([user1, user2])
    await db_session.flush()

    # Add to pool
    user1_pool = UserInPool(user_id=user1.user_id, pool_id=pool.id)
    user2_pool = UserInPool(user_id=user2.user_id, pool_id=pool.id)
    db_session.add_all([user1_pool, user2_pool])
    await db_session.commit()

    # Select duty for user1
    duty_manager = DutyManager(db_session)
    result1 = await duty_manager.select_random_duty(pool.id)

    first_selected = result1["user_id"]

    # Try to select again - should get different user
    # Refresh session to get updated data
    await db_session.refresh(user1_pool)
    await db_session.refresh(user2_pool)

    result2 = await duty_manager.select_random_duty(pool.id)

    # Results should be different users or one already assigned error
    assert result2 is not None
    if not result2.get("already_assigned"):
        assert result2["user_id"] != first_selected


@pytest.mark.asyncio
async def test_get_next_monday():
    """Test _get_next_monday calculation."""
    # Test on Monday - should get next Monday
    monday = datetime(2024, 1, 1)  # Monday
    next_mon = DutyManager._get_next_monday(monday)
    expected = datetime(2024, 1, 8)
    assert next_mon.date() == expected.date()

    # Test on Friday - should get next Monday
    friday = datetime(2024, 1, 5)  # Friday
    next_mon = DutyManager._get_next_monday(friday)
    expected = datetime(2024, 1, 8)
    assert next_mon.date() == expected.date()

    # Test on Sunday - should get next Monday
    sunday = datetime(2024, 1, 7)  # Sunday
    next_mon = DutyManager._get_next_monday(sunday)
    expected = datetime(2024, 1, 8)
    assert next_mon.date() == expected.date()
