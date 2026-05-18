"""Tests for the force-pick UX flow."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.handlers.force_pick import force_pick_command
from src.keyboards.force_pick import create_force_pick_user_keyboard, format_force_pick_user_name
from src.keyboards.week_selector import create_week_selector_keyboard


def _callbacks(markup):
    return [button.callback_data for row in markup.inline_keyboard for button in row]


def test_force_pick_user_keyboard_supports_user_without_username():
    """User picker should work for pool members without Telegram usernames."""
    keyboard = create_force_pick_user_keyboard(
        [
            {
                "user_id": 123456789,
                "first_name": "Ivan",
                "last_name": "Petrov",
                "username": None,
                "completed_cycle": False,
                "duty_status": None,
            }
        ]
    )

    button = keyboard.inline_keyboard[0][0]
    assert "Ivan Petrov" in button.text
    assert "@" not in button.text
    assert button.callback_data == "force_pick_user:123456789"


def test_force_pick_user_display_prefers_name_and_username():
    """Display helper should include both name and username when available."""
    user = SimpleNamespace(user_id=42, first_name="Maria", last_name="Ivanova", username="maria")

    assert format_force_pick_user_name(user) == "Maria Ivanova (@maria)"


def test_force_pick_week_keyboard_can_include_back_and_cancel_buttons():
    """Force-pick week picker should support navigation controls."""
    keyboard = create_week_selector_keyboard(
        action_prefix="force_pick_week",
        weeks_ahead=0,
        extra_data={"user_id": 123456789},
        back_callback_data="force_pick_back_to_users",
        cancel_callback_data="cancel_force_pick",
    )

    callbacks = _callbacks(keyboard)
    assert any(callback.startswith("force_pick_week:") for callback in callbacks)
    assert any("user_id:123456789" in callback for callback in callbacks)
    assert "force_pick_back_to_users" in callbacks
    assert "cancel_force_pick" in callbacks


@pytest.mark.asyncio
async def test_force_pick_rejects_private_chat():
    """Force pick is only available in group chats."""
    message = AsyncMock()
    message.chat.id = 123456789
    message.text = "/force_pick"

    await force_pick_command(message)

    message.answer.assert_called_once_with("⚠️ Эта команда работает только в групповых чатах!")


@pytest.mark.asyncio
async def test_force_pick_without_args_shows_empty_pool_message():
    """No-args force pick should open the picker flow and handle an empty pool."""
    message = AsyncMock()
    message.chat.id = -123456789
    message.chat.title = "Test Group"
    message.text = "/force_pick"

    pool = SimpleNamespace(id=1)
    session = AsyncMock()

    with (
        patch("src.handlers.force_pick.db_manager.async_session") as db_context,
        patch("src.handlers.force_pick.PoolRepository") as pool_repo_class,
        patch("src.handlers.force_pick.UserManager") as user_manager_class,
    ):
        db_context.return_value.__aenter__.return_value = session
        pool_repo = MagicMock()
        pool_repo.get_or_create = AsyncMock(return_value=pool)
        pool_repo_class.return_value = pool_repo

        user_manager = MagicMock()
        user_manager.get_pool_users = AsyncMock(return_value=[])
        user_manager_class.return_value = user_manager

        await force_pick_command(message)

    answer_text = message.answer.call_args.args[0]
    assert "В пуле дежурных пока нет участников" in answer_text
    assert "/join" in answer_text


@pytest.mark.asyncio
async def test_force_pick_without_args_shows_user_picker():
    """No-args force pick should show pool members as inline buttons."""
    message = AsyncMock()
    message.chat.id = -123456789
    message.chat.title = "Test Group"
    message.text = "/force_pick"

    pool = SimpleNamespace(id=1)
    session = AsyncMock()
    users = [
        {
            "user_id": 123456789,
            "first_name": "Ivan",
            "last_name": None,
            "username": None,
            "completed_cycle": False,
            "duty_status": None,
        }
    ]

    with (
        patch("src.handlers.force_pick.db_manager.async_session") as db_context,
        patch("src.handlers.force_pick.PoolRepository") as pool_repo_class,
        patch("src.handlers.force_pick.UserManager") as user_manager_class,
    ):
        db_context.return_value.__aenter__.return_value = session
        pool_repo = MagicMock()
        pool_repo.get_or_create = AsyncMock(return_value=pool)
        pool_repo_class.return_value = pool_repo

        user_manager = MagicMock()
        user_manager.get_pool_users = AsyncMock(return_value=users)
        user_manager_class.return_value = user_manager

        await force_pick_command(message)

    answer_text = message.answer.call_args.args[0]
    reply_markup = message.answer.call_args.kwargs["reply_markup"]
    assert "Выберите участника" in answer_text
    assert "force_pick_user:123456789" in _callbacks(reply_markup)


@pytest.mark.asyncio
async def test_force_pick_shortcut_uses_user_id_in_week_callbacks():
    """Shortcut /force_pick @username should keep working but pass user_id forward."""
    message = AsyncMock()
    message.chat.id = -123456789
    message.chat.title = "Test Group"
    message.text = "/force_pick @ivan"

    pool = SimpleNamespace(id=1)
    user = SimpleNamespace(user_id=123456789, first_name="Ivan", last_name=None, username="ivan")
    session = AsyncMock()

    with (
        patch("src.handlers.force_pick.db_manager.async_session") as db_context,
        patch("src.handlers.force_pick.PoolRepository") as pool_repo_class,
        patch("src.handlers.force_pick.UserRepository") as user_repo_class,
        patch("src.handlers.force_pick.UserPoolRepository") as user_pool_repo_class,
        patch("src.handlers.force_pick.get_week_statuses", new=AsyncMock(return_value={})),
    ):
        db_context.return_value.__aenter__.return_value = session

        pool_repo = MagicMock()
        pool_repo.get_or_create = AsyncMock(return_value=pool)
        pool_repo_class.return_value = pool_repo

        user_repo = MagicMock()
        user_repo.get_by_username = AsyncMock(return_value=user)
        user_repo_class.return_value = user_repo

        user_pool_repo = MagicMock()
        user_pool_repo.get_user_in_pool = AsyncMock(return_value=object())
        user_pool_repo_class.return_value = user_pool_repo

        await force_pick_command(message)

    reply_markup = message.answer.call_args.kwargs["reply_markup"]
    callbacks = _callbacks(reply_markup)
    assert any("user_id:123456789" in callback for callback in callbacks)
    assert not any("username:ivan" in callback for callback in callbacks)
