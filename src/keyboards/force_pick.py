"""Keyboards for force-picking a duty assignee."""

from collections.abc import Iterable
from typing import Any

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def format_force_pick_user_name(user: Any) -> str:
    """Format a Telegram user or user dict for force-pick messages."""
    if isinstance(user, dict):
        user_id = user.get("user_id")
        first_name = user.get("first_name")
        last_name = user.get("last_name")
        username = user.get("username")
    else:
        user_id = getattr(user, "user_id", None)
        first_name = getattr(user, "first_name", None)
        last_name = getattr(user, "last_name", None)
        username = getattr(user, "username", None)

    full_name = " ".join(part for part in (first_name, last_name) if part)
    if username:
        return f"{full_name} (@{username})" if full_name else f"@{username}"
    if full_name:
        return full_name
    return f"ID {user_id}"


def create_force_pick_user_keyboard(users: Iterable[dict[str, Any]]) -> InlineKeyboardMarkup:
    """Create inline keyboard with duty pool users."""
    builder = InlineKeyboardBuilder()

    for user in users:
        user_id = user["user_id"]
        builder.button(
            text=_format_user_button_text(user),
            callback_data=f"force_pick_user:{user_id}",
        )

    builder.button(text="❌ Отмена", callback_data="cancel_force_pick")
    builder.adjust(1)
    return builder.as_markup()


def _format_user_button_text(user: dict[str, Any]) -> str:
    status = _format_user_status(user)
    label = format_force_pick_user_name(user)
    text = f"{status} {label}"
    return _truncate(text, max_length=60)


def _format_user_status(user: dict[str, Any]) -> str:
    duty_status = user.get("duty_status")
    status_value = getattr(duty_status, "value", duty_status)

    if status_value == "confirmed":
        return "✅"
    if status_value == "pending":
        return "⏱️"
    if status_value in {"declined", "skipped"}:
        return "❌"
    if user.get("completed_cycle"):
        return "☑️"
    return "⏳"


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 1]}…"
