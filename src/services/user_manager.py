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

    async def get_pool_users(self, pool_id: int) -> list:
        """
        Get list of all users in pool with their details and duty status.

        Args:
            pool_id: Pool ID

        Returns:
            List of user dictionaries with details and duty status
        """
        from datetime import datetime
        from src.database.models import DutyStatus
        from src.database.repositories import DutyRepository

        users_in_pool = await self.pool_repo.get_active_users(pool_id)
        logger.info(
            f"get_pool_users: found {len(users_in_pool)} users_in_pool for pool_id={pool_id}"
        )

        # Get current week number
        current_week = datetime.now().isocalendar()[1]

        # Get duty repository to check current week assignments
        duty_repo = DutyRepository(self.session)

        result = []

        for user_in_pool in users_in_pool:
            logger.debug(f"Processing user_in_pool: user_id={user_in_pool.user_id}")
            user = await self.user_repo.get_by_id(user_in_pool.user_id)
            if user:
                logger.debug(f"Found user: {user.username or user.user_id}")

                # Check if user has pending/confirmed duty this week
                duty_status = None
                from sqlalchemy import and_, desc, select
                from src.database.models import DutyAssignment

                stmt = (
                    select(DutyAssignment)
                    .where(
                        and_(
                            DutyAssignment.pool_id == pool_id,
                            DutyAssignment.user_id == user.user_id,
                            DutyAssignment.week_number == current_week,
                        )
                    )
                    .order_by(desc(DutyAssignment.id))
                    .limit(1)
                )
                duty_result = await self.session.execute(stmt)
                duty_assignment = duty_result.scalar_one_or_none()

                if duty_assignment:
                    duty_status = duty_assignment.status

                result.append(
                    {
                        "user_id": user.user_id,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "username": user.username,
                        "completed_cycle": user_in_pool.has_completed_cycle,
                        "duty_status": duty_status,
                    }
                )
            else:
                logger.warning(f"User {user_in_pool.user_id} not found in telegram_users table")

        logger.info(f"get_pool_users: returning {len(result)} users")
        return result

    async def get_available_users(self, pool_id: int) -> list:
        """Get users who can be selected for duty (not completed cycle)."""
        users = await self.pool_repo.get_users_not_in_cycle(pool_id)
        return [user.user_id for user in users]
