"""Database engine and session management."""

from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
        self.async_session = async_sessionmaker(
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
            await self._migrate_sqlite_schema(conn)

    async def _migrate_sqlite_schema(self, conn) -> None:
        """Run lightweight SQLite migrations for existing databases."""
        if self.engine.dialect.name != "sqlite":
            return

        result = await conn.execute(text("PRAGMA table_info(duty_pools)"))
        columns = {row[1] for row in result.fetchall()}

        if "auto_pick_enabled" not in columns:
            await conn.execute(
                text(
                    "ALTER TABLE duty_pools "
                    "ADD COLUMN auto_pick_enabled BOOLEAN NOT NULL DEFAULT 1"
                )
            )

    async def drop_tables(self) -> None:
        """Drop all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()


# Global database manager instance
db_manager = DatabaseManager()
