"""Database engine and session management."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.database.models import Base


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: str = settings.DATABASE_URL):
        """
        Initialize database manager.

        Args:
            database_url: SQLAlchemy async database URL
        """
        self.engine = create_async_engine(
            database_url,
            echo=settings.DATABASE_ECHO,
            future=True,
        )
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session as async generator.

        Yields:
            AsyncSession instance
        """
        async with self.async_session() as session:
            yield session

    async def create_tables(self) -> None:
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()


# Global database manager instance
db_manager = DatabaseManager()
