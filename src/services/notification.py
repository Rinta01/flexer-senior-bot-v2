"""Notification service for sending messages to users and groups."""

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.database.repositories import DutyRepository, UserRepository
from src.utils.formatters import get_week_date_range
from src.utils.logger import setup_logging
from src.utils.validators import format_user_mention

logger = setup_logging(__name__)


class NotificationService:
    """Service for sending notifications via Telegram."""

    def __init__(self, bot: Bot, session):
        """
        Initialize notification service.

        Args:
            bot: Aiogram Bot instance
            session: Database session
        """
        self.bot = bot
        self.session = session
        self.user_repo = UserRepository(session)
        self.duty_repo = DutyRepository(session)

    async def announce_duty_assignment(
        self,
        group_id: int,
        user_id: int,
        week_number: int,
        assignment_id: int,
        is_automatic: bool = False,
    ) -> bool:
        """
        Announce duty assignment to group with confirmation buttons.

        Args:
            group_id: Telegram group ID
            user_id: User ID of selected duty
            week_number: Week number
            assignment_id: Duty assignment ID
            is_automatic: Whether this is automatic weekly selection

        Returns:
            True if successful
        """
        try:
            # Get user info
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return False

            # Format message
            mention = format_user_mention(user_id, user.username)
            date_range = get_week_date_range(week_number)

            # Add automatic selection prefix if needed
            auto_prefix = ""
            if is_automatic:
                auto_prefix = "⏰ <b>Время снова выбирать следующего дежурного!</b>\n\n"

            message_text = (
                f"{auto_prefix}"
                f"🎯 <b>Дежурный на неделю {date_range}</b>\n\n"
                f"Поздравляем, {mention}! 🎉\n\n"
                f"Ты выбран дежурным на эту неделю и отвечаешь за организацию "
                f"мероприятия для группы.\n\n"
                f"<b>Пожалуйста, подтверди или откажись:</b>"
            )

            # Create inline keyboard with confirmation buttons
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Принять",
                            callback_data=f"duty_confirm:{assignment_id}:{user_id}",
                        ),
                        InlineKeyboardButton(
                            text="❌ Отказаться",
                            callback_data=f"duty_decline:{assignment_id}:{user_id}",
                        ),
                    ]
                ]
            )

            # Send message
            message = await self.bot.send_message(
                chat_id=group_id,
                text=message_text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

            # Update message ID in database
            await self.duty_repo.update_message_id(assignment_id, message.message_id)
            await self.duty_repo.mark_notification_sent(assignment_id)
            await self.duty_repo.session.commit()

            logger.info(
                f"Announced duty for user {user_id} in group {group_id} (assignment {assignment_id})"
            )
            return True

        except Exception as e:
            logger.error(f"Error announcing duty: {e}")
            return False

    async def send_welcome_message(self, chat_id: int, chat_title: str) -> bool:
        """
        Send welcome message when bot joins group.

        Args:
            chat_id: Chat ID
            chat_title: Chat title

        Returns:
            True if successful
        """
        try:
            message_text = (
                f"👋 Привет, {chat_title}!\n\n"
                f"Я 'Флексер старший' - ваш помощник для управления дежурными. 🤖\n\n"
                f"Мой функционал:\n"
                f"• Каждую неделю назначаю нового дежурного\n"
                f"• Веду ротацию без повторений\n"
                f"• Помню всех участников\n\n"
                f"Команды:\n"
                f"/join - присоединиться к пулу дежурных\n"
                f"/leave - выйти из пула дежурных\n"
                f"/duty - узнать текущего дежурного\n"
                f"/help - подробная справка\n\n"
                f"Начните с /join чтобы участвовать в ротации! 💪"
            )

            await self.bot.send_message(
                chat_id=chat_id,
                text=message_text,
                parse_mode="HTML",
            )

            logger.info(f"Sent welcome message to {chat_title} ({chat_id})")
            return True

        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")
            return False

    async def send_pool_status(self, chat_id: int, pool_users_count: int) -> bool:
        """
        Send pool status message.

        Args:
            chat_id: Chat ID
            pool_users_count: Number of users in pool

        Returns:
            True if successful
        """
        try:
            message_text = (
                f"📊 <b>Статус пула дежурных</b>\n\n"
                f"Участников в пуле: <b>{pool_users_count}</b>\n\n"
                f"Каждую неделю один из вас будет выбран дежурным. "
                f"Дежурный не повторяется, пока все не побывают в роли."
            )

            await self.bot.send_message(
                chat_id=chat_id,
                text=message_text,
                parse_mode="HTML",
            )

            logger.info(f"Sent pool status to {chat_id}")
            return True

        except Exception as e:
            logger.error(f"Error sending pool status: {e}")
            return False
