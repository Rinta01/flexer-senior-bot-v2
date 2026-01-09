"""Unit tests for database repositories."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DutyPool, TelegramUser
from src.database.repositories import PoolRepository, UserRepository


@pytest.mark.asyncio
async def test_user_repository_get_or_create_new(
    db_session: AsyncSession,
    sample_user_data: dict,
):
    """Test creating new user."""
    user_repo = UserRepository(db_session)
    user = await user_repo.get_or_create(**sample_user_data)

    assert user.user_id == sample_user_data["user_id"]
    assert user.first_name == sample_user_data["first_name"]
    assert user.username == sample_user_data["username"]


@pytest.mark.asyncio
async def test_user_repository_get_existing(
    db_session: AsyncSession,
    sample_user_data: dict,
):
    """Test getting existing user."""
    user_repo = UserRepository(db_session)

    # Create first time
    user1 = await user_repo.get_or_create(**sample_user_data)

    # Get second time
    user2 = await user_repo.get_or_create(**sample_user_data)

    assert user1.id == user2.id
    assert user1.user_id == user2.user_id


@pytest.mark.asyncio
async def test_pool_repository_get_or_create(
    db_session: AsyncSession,
    sample_group_data: dict,
):
    """Test creating new pool."""
    pool_repo = PoolRepository(db_session)
    pool = await pool_repo.get_or_create(**sample_group_data)

    assert pool.group_id == sample_group_data["group_id"]
    assert pool.group_title == sample_group_data["group_title"]
    assert pool.is_active is True


@pytest.mark.asyncio
async def test_user_repository_update(
    db_session: AsyncSession,
    sample_user_data: dict,
):
    """Test updating user."""
    user_repo = UserRepository(db_session)

    # Create user
    user = await user_repo.get_or_create(**sample_user_data)

    # Update
    updated = await user_repo.update(
        user_id=sample_user_data["user_id"],
        first_name="Updated",
        is_active=False,
    )

    assert updated.first_name == "Updated"
    assert updated.is_active is False
