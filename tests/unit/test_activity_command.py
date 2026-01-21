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
        """Test that activity command shows week selection keyboard."""
        # Setup mocks
        mock_pool = AsyncMock()
        mock_pool.id = 1

        with (
            patch("src.handlers.activity.db_manager.async_session") as mock_db_context,
            patch("src.handlers.activity.PoolRepository") as mock_pool_repo_class,
        ):
            # Setup context and repos
            mock_db_context.return_value.__aenter__.return_value = mock_session
            mock_pool_repo = AsyncMock()
            mock_pool_repo_class.return_value = mock_pool_repo

            # Setup return values
            mock_pool_repo.get_by_id.return_value = mock_pool

            await show_activity_command(mock_message)

            # Should show week selection keyboard
            call_args = mock_message.answer.call_args[0][0]
            assert "📅 Выберите неделю для просмотра дежурного и активности:" in call_args
            # Check that keyboard was passed
            assert mock_message.answer.call_args[1]["reply_markup"] is not None

    async def test_activity_shows_confirmed_duty_with_activity(self, mock_message, mock_session):
        """Test that activity command shows week selection keyboard."""
        # Setup mocks
        mock_pool = AsyncMock()
        mock_pool.id = 1

        with (
            patch("src.handlers.activity.db_manager.async_session") as mock_db_context,
            patch("src.handlers.activity.PoolRepository") as mock_pool_repo_class,
        ):
            # Setup context and repos
            mock_db_context.return_value.__aenter__.return_value = mock_session
            mock_pool_repo = AsyncMock()
            mock_pool_repo_class.return_value = mock_pool_repo

            # Setup return values
            mock_pool_repo.get_by_id.return_value = mock_pool

            await show_activity_command(mock_message)

            # Should show week selection keyboard
            call_args = mock_message.answer.call_args[0][0]
            assert "📅 Выберите неделю для просмотра дежурного и активности:" in call_args
            # Check that keyboard was passed
            assert mock_message.answer.call_args[1]["reply_markup"] is not None

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
