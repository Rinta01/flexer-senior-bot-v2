"""Tests for lightweight database migrations."""

import pytest
from sqlalchemy import text

from src.database.engine import DatabaseManager


@pytest.mark.asyncio
async def test_create_tables_adds_auto_pick_enabled_to_existing_sqlite_database(tmp_path):
    """Existing SQLite duty_pools tables should get auto_pick_enabled with default true."""
    db_path = tmp_path / "legacy.db"
    manager = DatabaseManager(f"sqlite+aiosqlite:///{db_path}")

    try:
        async with manager.engine.begin() as conn:
            await conn.execute(
                text(
                    "CREATE TABLE duty_pools ("
                    "id INTEGER PRIMARY KEY, "
                    "group_id BIGINT UNIQUE, "
                    "group_title VARCHAR(255), "
                    "current_cycle INTEGER DEFAULT 1, "
                    "is_active BOOLEAN DEFAULT 1, "
                    "created_at DATETIME NOT NULL, "
                    "updated_at DATETIME NOT NULL"
                    ")"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO duty_pools "
                    "(id, group_id, group_title, current_cycle, is_active, created_at, updated_at) "
                    "VALUES (1, -100, 'Legacy Group', 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )

        await manager.create_tables()

        async with manager.engine.begin() as conn:
            columns_result = await conn.execute(text("PRAGMA table_info(duty_pools)"))
            columns = {row[1] for row in columns_result.fetchall()}
            value_result = await conn.execute(
                text("SELECT auto_pick_enabled FROM duty_pools WHERE group_id = -100")
            )

        assert "auto_pick_enabled" in columns
        assert value_result.scalar_one() == 1
    finally:
        await manager.close()
