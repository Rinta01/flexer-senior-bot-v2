"""Integration tests for handlers."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DutyPool
from src.services.user_manager import UserManager


@pytest.mark.asyncio
async def test_join_command_adds_user_to_pool(
    db_session: AsyncSession,
    sample_user_data: dict[str, int | str],
) -> None:
    """Test /join command adds user to pool."""
    # Create pool
    pool = DutyPool(group_id=-123, group_title="Test Group")
    db_session.add(pool)
    await db_session.commit()
    await db_session.refresh(pool)

    user_manager = UserManager(db_session)
    success, _ = await user_manager.add_user_to_pool(
        pool_id=pool.id,
        user_id=int(sample_user_data["user_id"]),
        first_name=str(sample_user_data["first_name"]),
        username=str(sample_user_data["username"]) if sample_user_data.get("username") else None,
        last_name=str(sample_user_data["last_name"]) if sample_user_data.get("last_name") else None,
    )

    assert success is True

    # Verify user in pool
    users_count = await user_manager.get_pool_users_count(pool.id)
    assert users_count == 1


@pytest.mark.asyncio
async def test_leave_command_removes_user(
    db_session: AsyncSession,
    sample_user_data: dict[str, int | str],
) -> None:
    """Test /leave command removes user from pool."""
    # Create pool
    pool = DutyPool(group_id=-123, group_title="Test Group")
    db_session.add(pool)
    await db_session.commit()
    await db_session.refresh(pool)

    # Create and add user
    user_manager = UserManager(db_session)
    success_add, _ = await user_manager.add_user_to_pool(
        pool_id=pool.id,
        user_id=int(sample_user_data["user_id"]),
        first_name=str(sample_user_data["first_name"]),
        username=str(sample_user_data["username"]) if sample_user_data.get("username") else None,
        last_name=str(sample_user_data["last_name"]) if sample_user_data.get("last_name") else None,
    )
    assert success_add is True

    # Remove user
    user_id_str = sample_user_data["user_id"]
    assert isinstance(user_id_str, (int, str)), "user_id must be int or str"
    success_remove, _ = await user_manager.remove_user_from_pool(
        user_id=int(user_id_str),
        pool_id=pool.id,
    )
    assert success_remove is True

    # Verify removed
    users_count = await user_manager.get_pool_users_count(pool.id)
    assert users_count == 0
