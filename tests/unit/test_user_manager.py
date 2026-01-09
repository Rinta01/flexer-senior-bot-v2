"""Unit tests for UserManager."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DutyPool, TelegramUser, UserInPool
from src.services.user_manager import UserManager


@pytest.mark.asyncio
async def test_add_user_to_pool(
    db_session: AsyncSession,
    sample_user_data: dict,
    sample_group_data: dict,
):
    """Test adding user to pool."""
    # Create pool
    pool = DutyPool(**sample_group_data)
    db_session.add(pool)
    await db_session.commit()

    # Add user to pool
    user_manager = UserManager(db_session)
    success, message = await user_manager.add_user_to_pool(
        pool_id=pool.id,
        **sample_user_data,
    )

    assert success is True
    assert "✅" in message


@pytest.mark.asyncio
async def test_add_duplicate_user_to_pool(
    db_session: AsyncSession,
    sample_user_data: dict,
    sample_group_data: dict,
):
    """Test adding same user twice to pool."""
    # Create pool
    pool = DutyPool(**sample_group_data)
    db_session.add(pool)
    await db_session.commit()

    # Add user first time
    user_manager = UserManager(db_session)
    success1, msg1 = await user_manager.add_user_to_pool(
        pool_id=pool.id,
        **sample_user_data,
    )
    assert success1 is True

    # Add same user second time - should succeed (idempotent)
    success2, msg2 = await user_manager.add_user_to_pool(
        pool_id=pool.id,
        **sample_user_data,
    )
    assert success2 is True


@pytest.mark.asyncio
async def test_remove_user_from_pool(
    db_session: AsyncSession,
    sample_user_data: dict,
    sample_group_data: dict,
):
    """Test removing user from pool."""
    # Create pool
    pool = DutyPool(**sample_group_data)
    db_session.add(pool)
    await db_session.commit()

    # Add user
    user_manager = UserManager(db_session)
    success_add, _ = await user_manager.add_user_to_pool(
        pool_id=pool.id,
        **sample_user_data,
    )
    assert success_add is True

    # Remove user
    success_remove, message = await user_manager.remove_user_from_pool(
        user_id=sample_user_data["user_id"],
        pool_id=pool.id,
    )
    assert success_remove is True
    assert "✅" in message


@pytest.mark.asyncio
async def test_remove_nonexistent_user_from_pool(
    db_session: AsyncSession,
    sample_group_data: dict,
):
    """Test removing user that wasn't in pool."""
    # Create pool
    pool = DutyPool(**sample_group_data)
    db_session.add(pool)
    await db_session.commit()

    # Try to remove non-existent user
    user_manager = UserManager(db_session)
    success, message = await user_manager.remove_user_from_pool(
        user_id=999,
        pool_id=pool.id,
    )

    assert success is False


@pytest.mark.asyncio
async def test_get_pool_users_count(
    db_session: AsyncSession,
    sample_user_data: dict,
    sample_group_data: dict,
):
    """Test getting count of users in pool."""
    # Create pool
    pool = DutyPool(**sample_group_data)
    db_session.add(pool)
    await db_session.commit()

    # Add multiple users
    user_manager = UserManager(db_session)
    await user_manager.add_user_to_pool(pool_id=pool.id, **sample_user_data)

    user2_data = sample_user_data.copy()
    user2_data["user_id"] = 999
    user2_data["username"] = "testuser2"
    await user_manager.add_user_to_pool(pool_id=pool.id, **user2_data)

    # Get count
    count = await user_manager.get_pool_users_count(pool.id)
    assert count == 2
