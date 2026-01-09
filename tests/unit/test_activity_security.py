"""Test activity security functionality."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, date

from src.handlers.activity import set_activity_command


class TestActivitySecurity:
    """Test security constraints for activity management."""

    @pytest.fixture
    def mock_message(self):
        """Create mock message for testing."""
        message = AsyncMock()
        message.chat.id = -1234567890  # Group chat
        message.from_user.id = 123456789
        message.from_user.first_name = "John"
        message.text = "/set_activity Test Event | Test Description | 15.01.2026 | 19:30"
        message.answer = AsyncMock()
        return message

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        return session

    async def test_set_activity_only_confirmed_duty(self, mock_message, mock_session):
        """Test that only confirmed duty can set activity."""
        # Setup mocks
        mock_pool = AsyncMock()
        mock_pool.id = 1

        mock_duty = AsyncMock()
        mock_duty.id = 1
        mock_duty.user_id = 123456789  # Same as message.from_user.id

        with (
            patch("src.handlers.activity.db_manager.async_session") as mock_db_context,
            patch("src.handlers.activity.PoolRepository") as mock_pool_repo_class,
            patch("src.handlers.activity.DutyRepository") as mock_duty_repo_class,
        ):

            # Setup context manager
            mock_db_context.return_value.__aenter__.return_value = mock_session

            # Setup repositories
            mock_pool_repo = AsyncMock()
            mock_duty_repo = AsyncMock()
            mock_pool_repo_class.return_value = mock_pool_repo
            mock_duty_repo_class.return_value = mock_duty_repo

            # Setup pool exists
            mock_pool_repo.get_by_id.return_value = mock_pool

            # Test case 1: No confirmed duty exists
            mock_duty_repo.get_current_confirmed_duty.return_value = None

            await set_activity_command(mock_message)

            mock_message.answer.assert_called_with(
                "ℹ️ На этой неделе нет подтвержденного дежурного. "
                "Сначала кто-то должен принять дежурство."
            )

            # Test case 2: Confirmed duty exists but different user
            mock_message.answer.reset_mock()
            different_duty = AsyncMock()
            different_duty.user_id = 999999999  # Different user
            mock_duty_repo.get_current_confirmed_duty.return_value = different_duty

            await set_activity_command(mock_message)

            mock_message.answer.assert_called_with(
                "❌ Только подтвержденный дежурный текущей недели может устанавливать активность."
            )

            # Test case 3: Confirmed duty exists and same user - should succeed
            mock_message.answer.reset_mock()
            mock_duty_repo.get_current_confirmed_duty.return_value = mock_duty
            mock_duty_repo.update_activity.return_value = mock_duty

            await set_activity_command(mock_message)

            # Should call update_activity and send success message
            mock_duty_repo.update_activity.assert_called_once()
            # Success message should contain "Активность на неделю установлена!"
            call_args = mock_message.answer.call_args[0][0]
            assert "Активность на неделю установлена!" in call_args

    async def test_set_activity_private_chat_blocked(self, mock_message):
        """Test that set_activity is blocked in private chats."""
        # Make it a private chat
        mock_message.chat.id = 123456789  # Positive ID = private chat

        await set_activity_command(mock_message)

        mock_message.answer.assert_called_with("⚠️ Эта команда работает только в групповых чатах!")

    async def test_set_activity_validates_current_week(self, mock_message, mock_session):
        """Test that duty validation checks current week."""
        mock_pool = AsyncMock()
        mock_pool.id = 1

        with (
            patch("src.handlers.activity.db_manager.async_session") as mock_db_context,
            patch("src.handlers.activity.PoolRepository") as mock_pool_repo_class,
            patch("src.handlers.activity.DutyRepository") as mock_duty_repo_class,
            patch("src.handlers.activity.date") as mock_date,
        ):

            # Setup current week
            current_week = 5
            mock_date.today.return_value.isocalendar.return_value = (2026, current_week, 1)

            # Setup context and repos
            mock_db_context.return_value.__aenter__.return_value = mock_session
            mock_pool_repo = AsyncMock()
            mock_duty_repo = AsyncMock()
            mock_pool_repo_class.return_value = mock_pool_repo
            mock_duty_repo_class.return_value = mock_duty_repo

            # Setup pool exists
            mock_pool_repo.get_by_id.return_value = mock_pool

            # No confirmed duty for current week
            mock_duty_repo.get_current_confirmed_duty.return_value = None

            await set_activity_command(mock_message)

            # Should call with current week
            mock_duty_repo.get_current_confirmed_duty.assert_called_with(mock_pool.id, current_week)
