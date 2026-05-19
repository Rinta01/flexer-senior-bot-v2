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
    assert pool.auto_pick_enabled is True


@pytest.mark.asyncio
async def test_pool_repository_get_auto_pick_enabled_pools(db_session: AsyncSession):
    """Test getting only active pools with scheduler auto-pick enabled."""
    enabled_pool = DutyPool(
        group_id=-1,
        group_title="Enabled",
        auto_pick_enabled=True,
        is_active=True,
    )
    disabled_pool = DutyPool(
        group_id=-2,
        group_title="Disabled",
        auto_pick_enabled=False,
        is_active=True,
    )
    inactive_pool = DutyPool(
        group_id=-3,
        group_title="Inactive",
        auto_pick_enabled=True,
        is_active=False,
    )
    db_session.add_all([enabled_pool, disabled_pool, inactive_pool])
    await db_session.commit()

    pool_repo = PoolRepository(db_session)
    pools = await pool_repo.get_auto_pick_enabled_pools()

    assert [pool.group_id for pool in pools] == [-1]


@pytest.mark.asyncio
async def test_pool_repository_set_auto_pick_enabled(
    db_session: AsyncSession,
    sample_group_data: dict,
):
    """Test updating scheduler auto-pick flag for a pool."""
    pool_repo = PoolRepository(db_session)
    await pool_repo.get_or_create(**sample_group_data)

    updated = await pool_repo.set_auto_pick_enabled(
        group_id=sample_group_data["group_id"],
        enabled=False,
    )

    assert updated is not None
    assert updated.auto_pick_enabled is False


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
