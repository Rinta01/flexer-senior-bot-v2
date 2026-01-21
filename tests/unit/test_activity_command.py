"""Test activity command functionality."""

import pytest
from unittest.mock import AsyncMock, patch

from src.handlers.activity import show_activity_command
from src.database.models import DutyStatus
from src.utils.formatters import get_week_date_range


class TestActivityCommand:
    """Test activity command functionality."""

    @pytest.fixture
    def mock_message(self):
        """Create mock message for testing."""
        message = AsyncMock()
        message.chat.id = -1234567890  # Group chat
        message.from_user.id = 123456789
        message.from_user.first_name = "John"
        message.answer = AsyncMock()
        return message

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        return session

    async def test_activity_shows_pending_duty(self, mock_message, mock_session):
        """Test that activity command shows pending duties."""
        # Setup mocks
        mock_pool = AsyncMock()
        mock_pool.id = 1

        mock_duty = AsyncMock()
        mock_duty.user_id = 123456789
        mock_duty.week_number = 2
        mock_duty.status = DutyStatus.PENDING
        mock_duty.activity_title = None
        mock_duty.activity_description = None
        mock_duty.activity_datetime = None

        mock_user = AsyncMock()
        mock_user.username = "john_doe"

        with (
            patch("src.handlers.activity.db_manager.async_session") as mock_db_context,
            patch("src.handlers.activity.PoolRepository") as mock_pool_repo_class,
            patch("src.handlers.activity.UserRepository") as mock_user_repo_class,
            patch("src.handlers.activity.DutyRepository") as mock_duty_repo_class,
            patch("src.handlers.activity.date") as mock_date,
        ):

            # Setup current week
            current_week = 2
            mock_date.today.return_value.isocalendar.return_value = (2026, current_week, 1)

            # Setup context and repos
            mock_db_context.return_value.__aenter__.return_value = mock_session
            mock_pool_repo = AsyncMock()
            mock_user_repo = AsyncMock()
            mock_duty_repo = AsyncMock()
            mock_pool_repo_class.return_value = mock_pool_repo
            mock_user_repo_class.return_value = mock_user_repo
            mock_duty_repo_class.return_value = mock_duty_repo

            # Setup return values
            mock_pool_repo.get_by_id.return_value = mock_pool
            mock_duty_repo.get_duty_for_week.return_value = mock_duty
            mock_user_repo.get_by_id.return_value = mock_user

            await show_activity_command(mock_message)

            # Should show duty information with PENDING status
            call_args = mock_message.answer.call_args[0][0]
            expected_date_range = get_week_date_range(2)  # Week 2
            assert "🎯 <b>Дежурный недели</b>" in call_args
            assert f"Неделя: {expected_date_range}" in call_args
            assert "pending" in call_args  # status.value is lowercase
            assert "⏳ Ожидаем подтверждения от дежурного." in call_args

    async def test_activity_shows_confirmed_duty_with_activity(self, mock_message, mock_session):
        """Test that activity command shows confirmed duty with activity."""
        from datetime import datetime, timezone

        # Setup mocks
        mock_pool = AsyncMock()
        mock_pool.id = 1

        mock_duty = AsyncMock()
        mock_duty.user_id = 123456789
        mock_duty.week_number = 2
        mock_duty.status = DutyStatus.CONFIRMED
        mock_duty.activity_title = "Test Event"
        mock_duty.activity_description = "Test Description"
        mock_duty.activity_datetime = datetime(2026, 1, 15, 19, 30, tzinfo=timezone.utc)

        mock_user = AsyncMock()
        mock_user.username = "john_doe"

        with (
            patch("src.handlers.activity.db_manager.async_session") as mock_db_context,
            patch("src.handlers.activity.PoolRepository") as mock_pool_repo_class,
            patch("src.handlers.activity.UserRepository") as mock_user_repo_class,
            patch("src.handlers.activity.DutyRepository") as mock_duty_repo_class,
            patch("src.handlers.activity.date") as mock_date,
        ):

            # Setup current week
            current_week = 2
            mock_date.today.return_value.isocalendar.return_value = (2026, current_week, 1)

            # Setup context and repos
            mock_db_context.return_value.__aenter__.return_value = mock_session
            mock_pool_repo = AsyncMock()
            mock_user_repo = AsyncMock()
            mock_duty_repo = AsyncMock()
            mock_pool_repo_class.return_value = mock_pool_repo
            mock_user_repo_class.return_value = mock_user_repo
            mock_duty_repo_class.return_value = mock_duty_repo

            # Setup return values
            mock_pool_repo.get_by_id.return_value = mock_pool
            mock_duty_repo.get_duty_for_week.return_value = mock_duty
            mock_user_repo.get_by_id.return_value = mock_user

            await show_activity_command(mock_message)

            # Should show duty and activity information
            call_args = mock_message.answer.call_args[0][0]
            expected_date_range = get_week_date_range(2)  # Week 2
            assert "🎯 <b>Дежурный недели</b>" in call_args
            assert f"Неделя: {expected_date_range}" in call_args
            assert "15.01.2026 в 19:30" in call_args
            assert "Увидимся на мероприятии! 🎉" in call_args

    async def test_activity_no_pool_found(self, mock_message, mock_session):
        """Test activity command when no pool exists."""
        with (
            patch("src.handlers.activity.db_manager.async_session") as mock_db_context,
            patch("src.handlers.activity.PoolRepository") as mock_pool_repo_class,
        ):

            # Setup context and repos
            mock_db_context.return_value.__aenter__.return_value = mock_session
            mock_pool_repo = AsyncMock()
            mock_pool_repo_class.return_value = mock_pool_repo

            # No pool exists
            mock_pool_repo.get_by_id.return_value = None

            await show_activity_command(mock_message)

            mock_message.answer.assert_called_with(
                "❌ Пул дежурных не найден для этой группы. "
                "Сначала кто-то должен присоединиться через /join"
            )
