"""Data access layer - repositories for database operations."""

from datetime import datetime
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DutyAssignment, DutyPool, TelegramUser, UserInPool
from src.utils.logger import setup_logging

logger = setup_logging(__name__)


class UserRepository:
    """Repository for TelegramUser operations."""

    def __init__(self, session: AsyncSession):
        """Initialize user repository."""
        self.session = session

    async def get_or_create(
        self,
        user_id: int,
        first_name: str,
        username: str | None = None,
        last_name: str | None = None,
    ) -> TelegramUser:
        """
        Get existing user or create new one.

        Args:
            user_id: Telegram user ID
            first_name: User's first name
            username: User's username (optional)
            last_name: User's last name (optional)

        Returns:
            TelegramUser instance
        """
        stmt = select(TelegramUser).where(TelegramUser.user_id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = TelegramUser(
                user_id=user_id,
                first_name=first_name,
                username=username,
                last_name=last_name,
            )
            self.session.add(user)
            await self.session.commit()
            logger.info(f"Created new user: {user}")

        return user

    async def get_by_id(self, user_id: int) -> TelegramUser | None:
        """Get user by Telegram user ID."""
        stmt = select(TelegramUser).where(TelegramUser.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> TelegramUser | None:
        """Get user by username (without @)."""
        stmt = select(TelegramUser).where(TelegramUser.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, user_id: int, **kwargs) -> TelegramUser | None:
        """Update user fields."""
        user = await self.get_by_id(user_id)
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            await self.session.commit()
        return user


class PoolRepository:
    """Repository for DutyPool operations."""

    def __init__(self, session: AsyncSession):
        """Initialize pool repository."""
        self.session = session

    async def get_or_create(
        self,
        group_id: int,
        group_title: str,
    ) -> DutyPool:
        """
        Get existing pool or create new one.

        Args:
            group_id: Telegram group ID
            group_title: Group title

        Returns:
            DutyPool instance
        """
        stmt = select(DutyPool).where(DutyPool.group_id == group_id)
        result = await self.session.execute(stmt)
        pool = result.scalar_one_or_none()

        if not pool:
            pool = DutyPool(group_id=group_id, group_title=group_title)
            self.session.add(pool)
            await self.session.commit()
            logger.info(f"Created new pool: {pool}")

        return pool

    async def get_by_id(self, group_id: int) -> DutyPool | None:
        """Get pool by group ID."""
        stmt = select(DutyPool).where(DutyPool.group_id == group_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_pool_id(self, pool_id: int) -> DutyPool | None:
        """Get pool by database ID."""
        stmt = select(DutyPool).where(DutyPool.id == pool_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_pools(self) -> list[DutyPool]:
        """
        Get all duty pools.

        Returns:
            List of all DutyPool instances
        """
        stmt = select(DutyPool)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class UserPoolRepository:
    """Repository for UserInPool operations."""

    def __init__(self, session: AsyncSession):
        """Initialize user pool repository."""
        self.session = session

    async def add_user_to_pool(self, user_id: int, pool_id: int) -> UserInPool:
        """Add user to pool."""
        # Check if already exists
        stmt = select(UserInPool).where(
            and_(UserInPool.user_id == user_id, UserInPool.pool_id == pool_id)
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"User {user_id} already in pool {pool_id}")
            return existing

        user_in_pool = UserInPool(user_id=user_id, pool_id=pool_id)
        self.session.add(user_in_pool)
        await self.session.commit()
        logger.info(f"Added user {user_id} to pool {pool_id}")
        return user_in_pool

    async def remove_user_from_pool(self, user_id: int, pool_id: int) -> bool:
        """Remove user from pool."""
        stmt = select(UserInPool).where(
            and_(UserInPool.user_id == user_id, UserInPool.pool_id == pool_id)
        )
        result = await self.session.execute(stmt)
        user_in_pool = result.scalar_one_or_none()

        if user_in_pool:
            await self.session.delete(user_in_pool)
            await self.session.commit()
            logger.info(f"Removed user {user_id} from pool {pool_id}")
            return True
        return False

    async def get_active_users(self, pool_id: int) -> list[UserInPool]:
        """Get all active users in pool."""
        stmt = (
            select(UserInPool).where(UserInPool.pool_id == pool_id).order_by(UserInPool.joined_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_users_not_in_cycle(self, pool_id: int) -> list[UserInPool]:
        """Get users who haven't completed current cycle."""
        stmt = (
            select(UserInPool)
            .where(
                and_(
                    UserInPool.pool_id == pool_id,
                    UserInPool.has_completed_cycle == False,
                )
            )
            .order_by(UserInPool.joined_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_in_pool(self, pool_id: int, user_id: int) -> UserInPool | None:
        """Get specific user in pool."""
        stmt = select(UserInPool).where(
            and_(UserInPool.pool_id == pool_id, UserInPool.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class DutyRepository:
    """Repository for DutyAssignment operations."""

    def __init__(self, session: AsyncSession):
        """Initialize duty repository."""
        self.session = session

    async def create_assignment(
        self,
        user_id: int,
        pool_id: int,
        week_number: int,
        assignment_date,
        cycle_number: int = 1,
    ) -> DutyAssignment:
        """Create duty assignment."""
        assignment = DutyAssignment(
            user_id=user_id,
            pool_id=pool_id,
            week_number=week_number,
            assignment_date=assignment_date,
            cycle_number=cycle_number,
        )
        self.session.add(assignment)
        await self.session.commit()
        logger.info(f"Created duty assignment: {assignment}")
        return assignment

    async def get_current_duty(self, pool_id: int, week_number: int) -> DutyAssignment | None:
        """Get confirmed duty assignment for specific week."""
        from src.database.models import DutyStatus

        stmt = select(DutyAssignment).where(
            and_(
                DutyAssignment.pool_id == pool_id,
                DutyAssignment.week_number == week_number,
                DutyAssignment.status == DutyStatus.CONFIRMED,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_duty_for_week(
        self, pool_id: int, year: int, week_number: int
    ) -> DutyAssignment | None:
        """Get duty assignment for specific week (any status)."""
        # For now, we match by week_number and assignment_date year
        # In future, we can add a year column to the model
        from datetime import datetime

        stmt = (
            select(DutyAssignment)
            .where(
                and_(
                    DutyAssignment.pool_id == pool_id,
                    DutyAssignment.week_number == week_number,
                )
            )
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        duties = result.scalars().all()

        # Filter by year from assignment_date
        for duty in duties:
            if duty.assignment_date.year == year:
                return duty

        return None

    async def get_pending_duties_for_week(
        self, pool_id: int, week_number: int, year: int | None = None
    ) -> list[DutyAssignment]:
        """Get all pending duty assignments for specific week."""
        from src.database.models import DutyStatus

        stmt = select(DutyAssignment).where(
            and_(
                DutyAssignment.pool_id == pool_id,
                DutyAssignment.week_number == week_number,
                DutyAssignment.status == DutyStatus.PENDING,
            )
        )
        result = await self.session.execute(stmt)
        duties = list(result.scalars().all())

        # Filter by year if provided
        if year is not None:
            duties = [d for d in duties if d.assignment_date.year == year]

        return duties

    async def mark_notification_sent(self, duty_id: int) -> None:
        """Mark notification as sent."""
        stmt = select(DutyAssignment).where(DutyAssignment.id == duty_id)
        result = await self.session.execute(stmt)
        duty = result.scalar_one_or_none()

        if duty:
            duty.notification_sent = True
            await self.session.commit()

    async def update_message_id(self, duty_id: int, message_id: int) -> None:
        """Update message ID for duty assignment."""
        stmt = select(DutyAssignment).where(DutyAssignment.id == duty_id)
        result = await self.session.execute(stmt)
        duty = result.scalar_one_or_none()

        if duty:
            duty.message_id = message_id
            await self.session.commit()

    async def update_status(self, duty_id: int, status) -> DutyAssignment | None:
        """Update duty assignment status."""
        stmt = select(DutyAssignment).where(DutyAssignment.id == duty_id)
        result = await self.session.execute(stmt)
        duty = result.scalar_one_or_none()

        if duty:
            old_status = duty.status
            duty.status = status
            await self.session.commit()
            logger.info(f"Updated duty {duty_id} status: {old_status.value} → {status.value}")
            return duty
        return None

    async def get_by_id(self, duty_id: int) -> DutyAssignment | None:
        """Get duty assignment by ID."""
        stmt = select(DutyAssignment).where(DutyAssignment.id == duty_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_activity(
        self, duty_id: int, title: str, description: str, activity_datetime: datetime
    ) -> DutyAssignment | None:
        """Update activity details for duty assignment."""
        from datetime import datetime

        stmt = select(DutyAssignment).where(DutyAssignment.id == duty_id)
        result = await self.session.execute(stmt)
        duty = result.scalar_one_or_none()

        if duty:
            duty.activity_title = title
            duty.activity_description = description
            duty.activity_datetime = activity_datetime
            duty.activity_set_at = datetime.now()
            await self.session.commit()
            logger.info(f"Updated activity for duty {duty_id}: {title}")
            return duty
        return None

    async def get_current_confirmed_duty(
        self, pool_id: int, week_number: int
    ) -> DutyAssignment | None:
        """Get current confirmed duty assignment for pool and week."""
        from src.database.models import DutyStatus

        stmt = select(DutyAssignment).where(
            and_(
                DutyAssignment.pool_id == pool_id,
                DutyAssignment.week_number == week_number,
                DutyAssignment.status == DutyStatus.CONFIRMED,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_current_confirmed_duty_by_group(self, group_id: int) -> DutyAssignment | None:
        """Get current confirmed duty assignment for group."""
        from src.database.models import DutyStatus
        from datetime import date

        current_week = date.today().isocalendar()[1]

        # Сначала получаем pool_id для группы
        pool_stmt = select(DutyPool.id).where(DutyPool.group_id == group_id)
        pool_result = await self.session.execute(pool_stmt)
        pool_id = pool_result.scalar_one_or_none()

        if not pool_id:
            return None

        # Теперь получаем подтвержденного дежурного
        stmt = select(DutyAssignment).where(
            and_(
                DutyAssignment.pool_id == pool_id,
                DutyAssignment.week_number == current_week,
                DutyAssignment.status == DutyStatus.CONFIRMED,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_duties(self, user_id: int, pool_id: int) -> list[DutyAssignment]:
        """Get all duty assignments for user in pool."""
        stmt = (
            select(DutyAssignment)
            .where(
                and_(
                    DutyAssignment.user_id == user_id,
                    DutyAssignment.pool_id == pool_id,
                )
            )
            .order_by(DutyAssignment.assignment_date)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_duties(self, pool_id: int, limit: int = 10) -> list[DutyAssignment]:
        """
        Get recent duty assignments for pool, ordered by date descending.

        Args:
            pool_id: Pool ID
            limit: Maximum number of records to return

        Returns:
            List of duty assignments, most recent first
        """
        stmt = (
            select(DutyAssignment)
            .where(DutyAssignment.pool_id == pool_id)
            .order_by(DutyAssignment.assignment_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
