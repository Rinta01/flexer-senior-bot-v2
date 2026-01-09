"""User pool management service."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories import UserPoolRepository, UserRepository
from src.utils.logger import setup_logging

logger = setup_logging(__name__)


class UserManager:
    """Manages user pool operations."""

    def __init__(self, session: AsyncSession):
        """Initialize user manager."""
        self.session = session
        self.user_repo = UserRepository(session)
        self.pool_repo = UserPoolRepository(session)

    async def add_user_to_pool(
        self,
        user_id: int,
        first_name: str,
        pool_id: int,
        username: str | None = None,
        last_name: str | None = None,
    ) -> tuple[bool, str]:
        """
        Add user to duty pool.

        Args:
            user_id: Telegram user ID
            first_name: User's first name
            pool_id: Pool ID to add user to
            username: User's username
            last_name: User's last name

        Returns:
            Tuple of (success, message)
        """
        try:
            # Create or get user
            user = await self.user_repo.get_or_create(
                user_id=user_id,
                first_name=first_name,
                username=username,
                last_name=last_name,
            )

            # Add to pool
            user_in_pool = await self.pool_repo.add_user_to_pool(user_id, pool_id)
            logger.info(f"User {user.username or user_id} added to pool {pool_id}")
            return True, "✅ Вы присоединились к пулу дежурных!"

        except Exception as e:
            logger.error(f"Error adding user to pool: {e}")
            return False, "❌ Произошла ошибка при добавлении в пул."

    async def remove_user_from_pool(self, user_id: int, pool_id: int) -> tuple[bool, str]:
        """
        Remove user from duty pool.

        Args:
            user_id: Telegram user ID
            pool_id: Pool ID

        Returns:
            Tuple of (success, message)
        """
        try:
            removed = await self.pool_repo.remove_user_from_pool(user_id, pool_id)
            if removed:
                logger.info(f"User {user_id} removed from pool {pool_id}")
                return True, "✅ Вы вышли из пула дежурных!"
            else:
                return False, "❌ Вы не в пуле дежурных."
        except Exception as e:
            logger.error(f"Error removing user from pool: {e}")
            return False, "❌ Произошла ошибка при удалении из пула."

    async def get_pool_users_count(self, pool_id: int) -> int:
        """Get count of active users in pool."""
        users = await self.pool_repo.get_active_users(pool_id)
        return len(users)

    async def get_available_users(self, pool_id: int) -> list:
        """Get users who can be selected for duty (not completed cycle)."""
        users = await self.pool_repo.get_users_not_in_cycle(pool_id)
        return [user.user_id for user in users]
