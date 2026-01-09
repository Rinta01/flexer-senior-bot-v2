"""Duty rotation management service."""

import random
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories import (
    DutyRepository,
    PoolRepository,
    UserPoolRepository,
)
from src.utils.logger import setup_logging

logger = setup_logging(__name__)


class DutyManager:
    """Manages duty rotation and selection logic."""

    def __init__(self, session: AsyncSession):
        """Initialize duty manager."""
        self.session = session
        self.duty_repo = DutyRepository(session)
        self.pool_repo = PoolRepository(session)
        self.user_pool_repo = UserPoolRepository(session)

    async def select_random_duty(self, pool_id: int) -> dict | None:
        """
        Select random duty from available users.

        Selection logic:
        - Prioritize users who haven't completed current cycle
        - Skip users already selected for current week
        - If all users completed cycle, reset cycle and select from all

        Args:
            pool_id: Pool ID

        Returns:
            Dict with selected user info or None if no users available
        """
        try:
            # Get pool
            pool = await self.pool_repo.get_by_id(pool_id)
            if not pool:
                logger.error(f"Pool {pool_id} not found")
                return None

            # Get current week number
            current_date = datetime.now()
            week_number = current_date.isocalendar()[1]

            # Check if already assigned for this week
            existing = await self.duty_repo.get_current_duty(pool_id, week_number)
            if existing:
                logger.info(f"Duty already assigned for pool {pool_id}, week {week_number}")
                return {
                    "user_id": existing.user_id,
                    "week_number": week_number,
                    "already_assigned": True,
                }

            # Get available users (not completed current cycle)
            available_users = await self.user_pool_repo.get_users_not_in_cycle(pool_id)

            if not available_users:
                logger.warning(f"No available users in pool {pool_id}, resetting cycle")
                # Reset cycle for all users
                all_users = await self.user_pool_repo.get_active_users(pool_id)
                for user in all_users:
                    user.has_completed_cycle = False
                await self.session.commit()

                available_users = all_users

            if not available_users:
                logger.error(f"No users in pool {pool_id}")
                return None

            # Select random user
            selected_user_in_pool = random.choice(available_users)
            selected_user_id = selected_user_in_pool.user_id

            # Create duty assignment
            next_monday = self._get_next_monday(current_date)
            assignment = await self.duty_repo.create_assignment(
                user_id=selected_user_id,
                pool_id=pool_id,
                week_number=week_number,
                assignment_date=next_monday,
                cycle_number=pool.current_cycle,
            )

            # Mark user as completed cycle
            selected_user_in_pool.has_completed_cycle = True
            await self.session.commit()

            logger.info(
                f"Selected user {selected_user_id} for duty in pool {pool_id}, "
                f"week {week_number}"
            )

            return {
                "user_id": selected_user_id,
                "week_number": week_number,
                "assignment_date": next_monday,
                "assignment_id": assignment.id,
                "already_assigned": False,
            }

        except Exception as e:
            logger.error(f"Error selecting random duty: {e}")
            return None

    async def get_current_duty(self, pool_id: int) -> dict | None:
        """Get current week's duty assignment."""
        try:
            current_date = datetime.now()
            week_number = current_date.isocalendar()[1]

            assignment = await self.duty_repo.get_current_duty(pool_id, week_number)
            if assignment:
                return {
                    "user_id": assignment.user_id,
                    "week_number": assignment.week_number,
                    "assignment_date": assignment.assignment_date,
                }
            return None

        except Exception as e:
            logger.error(f"Error getting current duty: {e}")
            return None

    @staticmethod
    def _get_next_monday(from_date: datetime) -> datetime:
        """
        Get next Monday from given date.

        Args:
            from_date: Reference date

        Returns:
            datetime for next Monday at 00:00
        """
        days_ahead = 0 - from_date.weekday()  # Monday is 0
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7

        next_monday = from_date + timedelta(days=days_ahead)
        return next_monday.replace(hour=0, minute=0, second=0, microsecond=0)

    async def get_user_duty_history(self, user_id: int, pool_id: int) -> list[dict]:
        """Get user's duty history."""
        try:
            duties = await self.duty_repo.get_user_duties(user_id, pool_id)
            return [
                {
                    "week_number": d.week_number,
                    "assignment_date": d.assignment_date,
                    "cycle_number": d.cycle_number,
                }
                for d in duties
            ]
        except Exception as e:
            logger.error(f"Error getting user duty history: {e}")
            return []
