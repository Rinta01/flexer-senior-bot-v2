"""Logging middleware for request logging."""

from typing import Any, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from src.utils.logger import setup_logging

logger = setup_logging(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging all incoming messages."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Any],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """
        Log incoming message and pass to handler.

        Args:
            handler: Next handler in chain
            event: Telegram event (Message, CallbackQuery, etc.)
            data: Middleware data

        Returns:
            Handler result
        """
        # Check if event is a Message
        if isinstance(event, Message):
            user_info = (
                f"{event.from_user.first_name} " f"(@{event.from_user.username or 'no_username'})"
                if event.from_user
                else "Unknown"
            )
            logger.debug(
                f"Message from {user_info} in chat {event.chat.id}: {event.text or '[no text]'}"
            )

        return await handler(event, data)
