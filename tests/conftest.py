"""Pytest configuration and shared fixtures."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_engine():
    """Create in-memory SQLite database for testing."""
    # Use SQLite in-memory for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests."""
    async_session = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with async_session() as session:
        yield session

        # Rollback transaction after test
        await session.rollback()


@pytest.fixture
def sample_user_data() -> dict:
    """Sample user data for tests."""
    return {
        "user_id": 123456789,
        "first_name": "Test",
        "username": "testuser",
        "last_name": "User",
    }


@pytest.fixture
def sample_group_data() -> dict:
    """Sample group data for tests."""
    return {
        "group_id": -987654321,
        "group_title": "Test Group",
    }
