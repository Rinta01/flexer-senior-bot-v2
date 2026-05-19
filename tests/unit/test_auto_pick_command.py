"""Tests for /auto_pick command."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.handlers.auto_pick import _parse_requested_state, auto_pick_command


def test_parse_requested_state():
    """Parser should accept common on/off aliases."""
    assert _parse_requested_state("on") is True
    assert _parse_requested_state("включить") is True
    assert _parse_requested_state("off") is False
    assert _parse_requested_state("выкл") is False
    assert _parse_requested_state("wat") is None


@pytest.mark.asyncio
async def test_auto_pick_rejects_private_chat():
    """Auto-pick settings are group-specific."""
    message = AsyncMock()
    message.chat.id = 123456789
    message.text = "/auto_pick"

    await auto_pick_command(message)

    message.answer.assert_called_once_with("⚠️ Эта команда работает только в групповых чатах!")


@pytest.mark.asyncio
async def test_auto_pick_shows_current_status():
    """No-args command should show current group status."""
    message = AsyncMock()
    message.chat.id = -100
    message.chat.title = "Test Group"
    message.text = "/auto_pick"

    pool = SimpleNamespace(id=1, auto_pick_enabled=True)
    session = AsyncMock()

    with (
        patch("src.handlers.auto_pick.db_manager.async_session") as db_context,
        patch("src.handlers.auto_pick.PoolRepository") as pool_repo_class,
    ):
        db_context.return_value.__aenter__.return_value = session
        pool_repo = MagicMock()
        pool_repo.get_or_create = AsyncMock(return_value=pool)
        pool_repo_class.return_value = pool_repo

        await auto_pick_command(message)

    answer_text = message.answer.call_args.args[0]
    assert "включен" in answer_text
    pool_repo.set_auto_pick_enabled.assert_not_called()


@pytest.mark.asyncio
async def test_auto_pick_updates_current_group_status():
    """Command with off/on argument should update current group's pool."""
    message = AsyncMock()
    message.chat.id = -100
    message.chat.title = "Test Group"
    message.text = "/auto_pick off"

    pool = SimpleNamespace(id=1, auto_pick_enabled=True)
    updated_pool = SimpleNamespace(id=1, auto_pick_enabled=False)
    session = AsyncMock()

    with (
        patch("src.handlers.auto_pick.db_manager.async_session") as db_context,
        patch("src.handlers.auto_pick.PoolRepository") as pool_repo_class,
    ):
        db_context.return_value.__aenter__.return_value = session
        pool_repo = MagicMock()
        pool_repo.get_or_create = AsyncMock(return_value=pool)
        pool_repo.set_auto_pick_enabled = AsyncMock(return_value=updated_pool)
        pool_repo_class.return_value = pool_repo

        await auto_pick_command(message)

    pool_repo.set_auto_pick_enabled.assert_awaited_once_with(-100, False)
    answer_text = message.answer.call_args.args[0]
    assert "выключен" in answer_text


@pytest.mark.asyncio
async def test_auto_pick_rejects_unknown_argument():
    """Unknown argument should return usage and avoid DB work."""
    message = AsyncMock()
    message.chat.id = -100
    message.text = "/auto_pick maybe"

    await auto_pick_command(message)

    answer_text = message.answer.call_args.args[0]
    assert "Не понял значение" in answer_text
