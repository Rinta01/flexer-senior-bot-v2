"""Duty rotation management service."""

import random
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DutyStatus
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
            # Get pool by database ID
            pool = await self.pool_repo.get_by_pool_id(pool_id)
            if not pool:
                logger.error(f"Pool {pool_id} not found")
                return None

            # Get current week number
            current_date = datetime.now()
            current_year = current_date.year
            week_number = current_date.isocalendar()[1]

            # Check if already confirmed for this week
            existing = await self.duty_repo.get_duty_for_week(pool_id, current_year, week_number)
            if existing:
                if existing.status == DutyStatus.CONFIRMED:
                    logger.info(f"Duty already confirmed for pool {pool_id}, week {week_number}")
                    return {
                        "user_id": existing.user_id,
                        "week_number": week_number,
                        "already_assigned": True,
                    }
                elif existing.status == DutyStatus.PENDING:
                    logger.info(f"Duty pending for pool {pool_id}, week {week_number}")
                    return {
                        "user_id": existing.user_id,
                        "week_number": week_number,
                        "already_assigned": True,
                        "error": "all_pending",
                        "pending_duties": [existing],
                    }
                # If status is SKIPPED/DECLINED, continue with new assignment

            # Get users with pending assignments for this week
            pending_duties = await self.duty_repo.get_pending_duties_for_week(
                pool_id, week_number, current_year
            )
            pending_user_ids = {duty.user_id for duty in pending_duties}

            # Get available users (not completed current cycle)
            available_users = await self.user_pool_repo.get_users_not_in_cycle(pool_id)

            # Filter out users with pending assignments
            available_users = [
                user for user in available_users if user.user_id not in pending_user_ids
            ]

            # Track if cycle was reset
            cycle_reset = False

            if not available_users:
                logger.warning(f"No available users in pool {pool_id}, resetting cycle")
                # Reset cycle for all users
                all_users = await self.user_pool_repo.get_active_users(pool_id)
                for user in all_users:
                    user.has_completed_cycle = False
                await self.session.commit()

                cycle_reset = True

                # Filter out users with pending assignments again
                available_users = [
                    user for user in all_users if user.user_id not in pending_user_ids
                ]

            if not available_users:
                if pending_user_ids:
                    logger.info(
                        f"All users in pool {pool_id} have pending assignments for week {week_number}"
                    )
                    return {
                        "error": "all_pending",
                        "pending_duties": pending_duties,  # Return pending duties for re-announcement
                        "week_number": week_number,
                    }
                else:
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
                "cycle_reset": cycle_reset,
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

    async def assign_duty_to_user(self, pool_id: int, user_id: int) -> dict | None:
        """
        Assign duty to specific user.

        Args:
            pool_id: Pool ID
            user_id: User ID to assign duty to

        Returns:
            Dict with assignment info or None if cannot assign
        """
        try:
            # Get pool by database ID
            pool = await self.pool_repo.get_by_pool_id(pool_id)
            if not pool:
                logger.error(f"Pool {pool_id} not found")
                return None

            # Get current week number
            current_date = datetime.now()
            week_number = current_date.isocalendar()[1]

            # Check if already confirmed for this week
            existing = await self.duty_repo.get_current_duty(pool_id, week_number)
            if existing:
                logger.info(f"Duty already confirmed for pool {pool_id}, week {week_number}")
                return None

            # Check if user is in pool
            user_in_pool = await self.user_pool_repo.get_user_in_pool(pool_id, user_id)
            if not user_in_pool:
                logger.error(f"User {user_id} not in pool {pool_id}")
                return None

            # Create duty assignment
            next_monday = self._get_next_monday(current_date)
            assignment = await self.duty_repo.create_assignment(
                user_id=user_id,
                pool_id=pool_id,
                week_number=week_number,
                assignment_date=next_monday,
                cycle_number=pool.current_cycle,
            )

            # Mark user as completed cycle
            user_in_pool.has_completed_cycle = True
            await self.session.commit()

            logger.info(f"Assigned user {user_id} for duty in pool {pool_id}, week {week_number}")

            return {
                "user_id": user_id,
                "week_number": week_number,
                "assignment_date": next_monday,
                "assignment_id": assignment.id,
            }

        except Exception as e:
            logger.error(f"Error assigning duty to user: {e}")
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

    async def select_random_duty_for_week(
        self, pool_id: int, year: int, week_number: int
    ) -> dict | None:
        """
        Select random duty for a specific week.

        Args:
            pool_id: Pool ID
            year: Year number
            week_number: ISO week number

        Returns:
            Dict with assignment info or None if cannot assign
        """
        try:
            pool = await self.pool_repo.get_by_pool_id(pool_id)
            if not pool:
                logger.error(f"Pool {pool_id} not found")
                return None

            # Check if already assigned for this week
            existing = await self.duty_repo.get_duty_for_week(pool_id, year, week_number)
            if existing:
                # /pick can only work if the existing duty was SKIPPED (declined)
                if existing.status == DutyStatus.CONFIRMED:
                    logger.info(
                        f"Duty already confirmed for pool {pool_id}, week {week_number}/{year}"
                    )
                    return {
                        "user_id": existing.user_id,
                        "week_number": week_number,
                        "year": year,
                        "already_assigned": True,
                    }
                elif existing.status == DutyStatus.PENDING:
                    logger.info(f"Duty pending for pool {pool_id}, week {week_number}/{year}")
                    return {
                        "user_id": existing.user_id,
                        "week_number": week_number,
                        "year": year,
                        "already_assigned": True,
                        "status": "pending",
                    }
                # If status is SKIPPED, continue with new assignment

            # Get pending assignments for this week
            pending_duties = await self.duty_repo.get_pending_duties_for_week(
                pool_id, week_number, year
            )
            pending_user_ids = {duty.user_id for duty in pending_duties}

            # Get available users (not completed current cycle)
            available_users = await self.user_pool_repo.get_users_not_in_cycle(pool_id)
            available_users = [u for u in available_users if u.user_id not in pending_user_ids]

            if not available_users:
                logger.warning(f"No available users in pool {pool_id}, resetting cycle")
                # Reset cycle
                all_users = await self.user_pool_repo.get_active_users(pool_id)
                for user in all_users:
                    user.has_completed_cycle = False
                await self.session.commit()

                available_users = [u for u in all_users if u.user_id not in pending_user_ids]

            if not available_users:
                if pending_user_ids:
                    logger.info(
                        f"All users in pool {pool_id} have pending assignments for week {week_number}/{year}"
                    )
                    return {"error": "all_pending", "week_number": week_number, "year": year}
                logger.error(f"No users in pool {pool_id}")
                return None

            # Select random user
            selected_user_in_pool = random.choice(available_users)
            selected_user_id = selected_user_in_pool.user_id

            # Calculate Monday of the target week
            monday = self._get_monday_of_week(year, week_number)

            # Create assignment
            assignment = await self.duty_repo.create_assignment(
                user_id=selected_user_id,
                pool_id=pool_id,
                week_number=week_number,
                assignment_date=monday,
                cycle_number=pool.current_cycle,
            )

            # Mark user as completed cycle
            selected_user_in_pool.has_completed_cycle = True
            await self.session.commit()

            logger.info(
                f"Selected user {selected_user_id} for duty in pool {pool_id}, "
                f"week {week_number}/{year}"
            )

            return {
                "user_id": selected_user_id,
                "week_number": week_number,
                "year": year,
                "assignment_date": monday,
                "assignment_id": assignment.id,
                "already_assigned": False,
            }

        except Exception as e:
            logger.error(f"Error selecting random duty for week: {e}", exc_info=True)
            return None

    async def assign_duty_to_user_for_week(
        self, pool_id: int, user_id: int, year: int, week_number: int, force: bool = False
    ) -> dict | None:
        """
        Assign duty to specific user for specific week.

        Args:
            pool_id: Pool ID
            user_id: User ID
            year: Year number
            week_number: ISO week number
            force: If True, replaces existing duty even if not SKIPPED (for /force_pick)

        Returns:
            Dict with assignment info, or dict with 'needs_confirmation' if existing duty found
        """
        try:
            pool = await self.pool_repo.get_by_pool_id(pool_id)
            if not pool:
                logger.error(f"Pool {pool_id} not found")
                return None

            # Check if already assigned for this week
            existing = await self.duty_repo.get_duty_for_week(pool_id, year, week_number)
            if existing:
                # If force=False and duty exists (even SKIPPED), ask for confirmation
                if not force:
                    logger.info(
                        f"Duty exists for pool {pool_id}, week {week_number}/{year} - needs confirmation"
                    )
                    return {
                        "needs_confirmation": True,
                        "existing_duty": existing,
                        "existing_status": existing.status.value,
                        "week_number": week_number,
                        "year": year,
                    }
                # If force=True, mark old duty as FORCE_REMOVED and reset user's cycle
                logger.info(
                    f"Force replacing duty {existing.id} for pool {pool_id}, week {week_number}/{year} "
                    f"with status {existing.status.value}"
                )
                existing.status = DutyStatus.FORCE_REMOVED

                # Reset has_completed_cycle for replaced user
                replaced_user = await self.user_pool_repo.get_user_in_pool(
                    pool_id, existing.user_id
                )
                if replaced_user and replaced_user.has_completed_cycle:
                    logger.info(
                        f"Resetting has_completed_cycle for replaced user {existing.user_id}"
                    )
                    replaced_user.has_completed_cycle = False

            # Check if user is in pool
            user_in_pool = await self.user_pool_repo.get_user_in_pool(pool_id, user_id)
            if not user_in_pool:
                logger.error(f"User {user_id} not in pool {pool_id}")
                return None

            # Calculate Monday of the target week
            monday = self._get_monday_of_week(year, week_number)

            # Create assignment
            assignment = await self.duty_repo.create_assignment(
                user_id=user_id,
                pool_id=pool_id,
                week_number=week_number,
                assignment_date=monday,
                cycle_number=pool.current_cycle,
            )

            # Mark user as completed cycle
            user_in_pool.has_completed_cycle = True
            await self.session.commit()

            logger.info(
                f"Assigned user {user_id} for duty in pool {pool_id}, week {week_number}/{year}"
            )

            return {
                "user_id": user_id,
                "week_number": week_number,
                "year": year,
                "assignment_date": monday,
                "assignment_id": assignment.id,
            }

        except Exception as e:
            logger.error(f"Error assigning duty to user for week: {e}", exc_info=True)
            return None

    @staticmethod
    def _get_monday_of_week(year: int, week: int) -> datetime:
        """
        Get Monday date for a specific ISO week.

        Args:
            year: Year number
            week: ISO week number (1-53)

        Returns:
            datetime for Monday of that week at 00:00
        """
        jan_first = datetime(year, 1, 1)
        days_to_monday = (7 - jan_first.weekday()) % 7
        if jan_first.weekday() > 3:
            days_to_monday += 7

        first_monday = jan_first + timedelta(days=days_to_monday)
        target_monday = first_monday + timedelta(weeks=week - 1)

        return target_monday.replace(hour=0, minute=0, second=0, microsecond=0)
