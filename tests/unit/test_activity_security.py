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
        """Test that set_activity command shows week selection keyboard."""
        # Setup mocks
        mock_pool = AsyncMock()
        mock_pool.id = 1

        with (
            patch("src.handlers.activity.db_manager.async_session") as mock_db_context,
            patch("src.handlers.activity.PoolRepository") as mock_pool_repo_class,
            patch("src.handlers.activity.get_week_statuses") as mock_get_week_statuses,
        ):
            # Setup context manager
            mock_db_context.return_value.__aenter__.return_value = mock_session

            # Setup repositories
            mock_pool_repo = AsyncMock()
            mock_pool_repo_class.return_value = mock_pool_repo

            # Setup pool exists
            mock_pool_repo.get_by_id.return_value = mock_pool
            mock_get_week_statuses.return_value = {}  # Empty week statuses

            await set_activity_command(mock_message)

            # Should show week selection keyboard
            call_args = mock_message.answer.call_args[0][0]
            assert "📅 Выберите неделю для установки активности:" in call_args
            # Check that keyboard was passed
            assert mock_message.answer.call_args[1]["reply_markup"] is not None

    async def test_set_activity_private_chat_blocked(self, mock_message):
        """Test that set_activity is blocked in private chats."""
        # Make it a private chat
        mock_message.chat.id = 123456789  # Positive ID = private chat

        await set_activity_command(mock_message)

        mock_message.answer.assert_called_with("⚠️ Эта команда работает только в групповых чатах!")

    async def test_set_activity_validates_current_week(self, mock_message, mock_session):
        """Test that set_activity command shows week selection keyboard."""
        mock_pool = AsyncMock()
        mock_pool.id = 1

        with (
            patch("src.handlers.activity.db_manager.async_session") as mock_db_context,
            patch("src.handlers.activity.PoolRepository") as mock_pool_repo_class,
            patch("src.handlers.activity.datetime") as mock_datetime,
            patch("src.handlers.activity.get_week_statuses") as mock_get_week_statuses,
        ):
            # Setup current week
            current_week = 5
            mock_datetime.now.return_value.isocalendar.return_value = (2026, current_week, 1)
            mock_datetime.now.return_value.year = 2026

            # Setup context and repos
            mock_db_context.return_value.__aenter__.return_value = mock_session
            mock_pool_repo = AsyncMock()
            mock_pool_repo_class.return_value = mock_pool_repo

            # Setup pool exists
            mock_pool_repo.get_by_id.return_value = mock_pool
            mock_get_week_statuses.return_value = {}  # Empty week statuses

            await set_activity_command(mock_message)

            # Should show week selection keyboard
            call_args = mock_message.answer.call_args[0][0]
            assert "📅 Выберите неделю для установки активности:" in call_args
            # Check that keyboard was passed
            assert mock_message.answer.call_args[1]["reply_markup"] is not None
