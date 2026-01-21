"""Week selection callback handlers."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from src.database.engine import db_manager
from src.database.models import DutyStatus
from src.database.repositories import (
    DutyRepository,
    PoolRepository,
    UserRepository,
)
from src.keyboards.week_selector import format_week_display, parse_week_callback
from src.services.duty_manager import DutyManager
from src.services.notification import NotificationService
from src.utils.formatters import get_week_date_range
from src.utils.logger import setup_logging
from src.utils.validators import format_user_mention

from .activity import format_activity_info

logger = setup_logging(__name__)

router = Router()


@router.callback_query(F.data.startswith("pick_week:"))
async def handle_pick_week_callback(callback: CallbackQuery) -> None:
    """Handle week selection for /pick command (random selection)."""
    try:
        if (
            not callback.data
            or not callback.message
            or not isinstance(callback.message, Message)
            or not callback.message.chat
        ):
            return

        # Parse callback data
        data = parse_week_callback(callback.data)
        year = data["year"]
        week_number = data["week"]

        # Answer callback to remove loading state
        await callback.answer()

        async with db_manager.async_session() as session:
            # Get pool
            pool_repo = PoolRepository(session)
            pool = await pool_repo.get_or_create(
                group_id=callback.message.chat.id,
                group_title=callback.message.chat.title or "Unknown Group",
            )

            # Select random duty for the week
            duty_manager = DutyManager(session)
            result = await duty_manager.select_random_duty_for_week(pool.id, year, week_number)

            if not result:
                await callback.message.edit_text(
                    f"❌ Не удалось выбрать дежурного на {format_week_display(week_number, year)}.\n"
                    f"Возможно, в пуле нет участников."
                )
                return

            if result.get("already_assigned"):
                await callback.message.edit_text(
                    f"ℹ️ На {format_week_display(week_number, year)} уже назначен дежурный."
                )
                return

            if result.get("error") == "all_pending":
                await callback.message.edit_text(
                    f"⚠️ На {format_week_display(week_number, year)} все пользователи уже имеют ожидающие назначения."
                )
                return

            # Get user info
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(result["user_id"])

            if not user:
                await callback.message.edit_text("❌ Ошибка: пользователь не найден.")
                return

            # Send notification
            if not callback.message.bot:
                await callback.message.edit_text("❌ Ошибка: бот недоступен.")
                return

            notification_service = NotificationService(callback.message.bot, session)
            success = await notification_service.announce_duty_assignment(
                group_id=callback.message.chat.id,
                user_id=user.user_id,
                week_number=week_number,
                assignment_id=result["assignment_id"],
                is_automatic=False,
                year=year,
            )

            if success:
                user_mention = f"@{user.username}" if user.username else user.first_name
                await callback.message.edit_text(
                    f"✅ Дежурный на {format_week_display(week_number, year)} выбран: {user_mention}\n\n"
                    f"Ожидается подтверждение."
                )
                logger.info(
                    f"Random duty selected for week {week_number}/{year}: user {user.user_id} "
                    f"in pool {pool.id}"
                )
            else:
                await callback.message.edit_text(f"❌ Ошибка при отправке уведомления дежурному.")

    except Exception as e:
        logger.error(f"Error handling pick_week callback: {e}", exc_info=True)
        if callback.message and isinstance(callback.message, Message):
            await callback.message.edit_text("❌ Произошла ошибка при выборе дежурного.")


@router.callback_query(F.data.startswith("force_pick_week:"))
async def handle_force_pick_week_callback(callback: CallbackQuery) -> None:
    """Handle week selection for /force_pick command (specific user)."""
    try:
        if (
            not callback.data
            or not callback.message
            or not isinstance(callback.message, Message)
            or not callback.message.chat
        ):
            return

        # Parse callback data
        data = parse_week_callback(callback.data)
        year = data["year"]
        week_number = data["week"]
        username = data.get("username")

        if not username:
            await callback.answer("❌ Ошибка: username не указан", show_alert=True)
            return

        # Answer callback
        await callback.answer()

        async with db_manager.async_session() as session:
            # Get pool
            pool_repo = PoolRepository(session)
            pool = await pool_repo.get_or_create(
                group_id=callback.message.chat.id,
                group_title=callback.message.chat.title or "Unknown Group",
            )

            # Find user
            user_repo = UserRepository(session)
            target_user = await user_repo.get_by_username(username)

            if not target_user:
                await callback.message.edit_text(
                    f"❌ Пользователь @{username} не найден в системе."
                )
                return

            # Assign duty to user for the week
            duty_manager = DutyManager(session)
            result = await duty_manager.assign_duty_to_user_for_week(
                pool.id, target_user.user_id, year, week_number
            )

            if not result:
                await callback.message.edit_text(
                    f"❌ Не удалось назначить @{username} дежурным на {format_week_display(week_number, year)}.\n"
                    f"Возможно, на эту неделю уже есть подтвержденный дежурный."
                )
                return

            # Send notification
            if not callback.message.bot:
                await callback.message.edit_text("❌ Ошибка: бот недоступен.")
                return

            notification_service = NotificationService(callback.message.bot, session)
            success = await notification_service.announce_duty_assignment(
                group_id=callback.message.chat.id,
                user_id=target_user.user_id,
                week_number=week_number,
                assignment_id=result["assignment_id"],
                is_automatic=False,
                year=year,
            )

            if success:
                await callback.message.edit_text(
                    f"✅ Уведомление отправлено пользователю @{username} на {format_week_display(week_number, year)}.\n\n"
                    f"Ожидается подтверждение дежурства."
                )
                logger.info(
                    f"Force picked duty for week {week_number}/{year}: user @{username} (ID {target_user.user_id}) "
                    f"in pool {pool.id}"
                )
            else:
                await callback.message.edit_text("❌ Ошибка при отправке уведомления.")

    except Exception as e:
        logger.error(f"Error handling force_pick_week callback: {e}", exc_info=True)
        if callback.message and isinstance(callback.message, Message):
            await callback.message.edit_text("❌ Произошла ошибка при назначении дежурного.")


@router.callback_query(F.data.startswith("activity_week:"))
async def handle_activity_week_callback(callback: CallbackQuery) -> None:
    """Handle week selection for /activity command."""
    try:
        if (
            not callback.data
            or not callback.message
            or not isinstance(callback.message, Message)
            or not callback.message.chat
        ):
            return

        # Parse callback data
        data = parse_week_callback(callback.data)
        year = data["year"]
        week_number = data["week"]

        # Answer callback
        await callback.answer()

        async with db_manager.async_session() as session:
            pool_repo = PoolRepository(session)
            user_repo = UserRepository(session)
            duty_repo = DutyRepository(session)

            # Get pool
            pool = await pool_repo.get_by_id(callback.message.chat.id)
            if not pool:
                await callback.message.edit_text("❌ Пул дежурных не найден для этой группы.")
                return

            # Get duty for the selected week
            duty_assignment = await duty_repo.get_duty_for_week(
                pool_id=pool.id, year=year, week_number=week_number
            )

            if not duty_assignment:
                await callback.message.edit_text(
                    f"ℹ️ На {format_week_display(week_number, year)} дежурный ещё не выбран."
                )
                return

            # Get user info
            user = await user_repo.get_by_id(duty_assignment.user_id)
            if not user:
                await callback.message.edit_text("❌ Не удалось найти информацию о дежурном.")
                return

            # Use pure function to format response
            response = format_activity_info(duty_assignment, user)

            await callback.message.edit_text(response, parse_mode="HTML")
            logger.info(
                f"Activity shown for week {week_number}/{year} in group {callback.message.chat.id}"
            )

    except Exception as e:
        logger.error(f"Error handling activity_week callback: {e}", exc_info=True)
        if callback.message and isinstance(callback.message, Message):
            await callback.message.edit_text(
                "❌ Произошла ошибка при получении информации об активности."
            )


@router.callback_query(F.data.startswith("set_activity_week:"))
async def handle_set_activity_week_callback(callback: CallbackQuery) -> None:
    """Handle week selection for /set_activity command."""
    try:
        if (
            not callback.data
            or not callback.message
            or not isinstance(callback.message, Message)
            or not callback.message.chat
            or not callback.from_user
        ):
            return

        # Parse callback data
        data = parse_week_callback(callback.data)
        year = data["year"]
        week_number = data["week"]
        user_id_str = data.get("user_id", "0")

        # Check if the callback is from the same user who initiated the command
        if str(callback.from_user.id) != user_id_str:
            await callback.answer(
                "❌ Только пользователь, вызвавший команду, может выбрать неделю", show_alert=True
            )
            return

        # Answer callback
        await callback.answer()

        async with db_manager.async_session() as session:
            pool_repo = PoolRepository(session)
            duty_repo = DutyRepository(session)

            # Get pool
            pool = await pool_repo.get_by_id(callback.message.chat.id)
            if not pool:
                await callback.message.edit_text("❌ Пул дежурных не найден для этой группы.")
                return

            # Check if duty exists for this week
            duty_assignment = await duty_repo.get_duty_for_week(
                pool_id=pool.id, year=year, week_number=week_number
            )

            if not duty_assignment:
                await callback.message.edit_text(
                    f"❌ На {format_week_display(week_number, year)} дежурный ещё не выбран.\n"
                    f"Сначала назначьте дежурного командой /pick или /force_pick"
                )
                return

            # Log duty status for debugging
            logger.info(
                f"Duty assignment found for week {week_number}/{year}: "
                f"ID={duty_assignment.id}, user_id={duty_assignment.user_id}, "
                f"status={duty_assignment.status}, assignment_date={duty_assignment.assignment_date}"
            )

            # Check if user is the confirmed duty for this week
            if duty_assignment.status != DutyStatus.CONFIRMED:
                await callback.message.edit_text(
                    f"❌ Дежурный на {format_week_display(week_number, year)} ещё не подтвердил назначение.\n"
                    f"Только подтвержденный дежурный может устанавливать активность."
                )
                return

            if duty_assignment.user_id != callback.from_user.id:
                await callback.message.edit_text(
                    f"❌ Вы не являетесь дежурным на {format_week_display(week_number, year)}.\n"
                    f"Только подтвержденный дежурный этой недели может устанавливать активность."
                )
                return

            # Prompt user to enter activity details
            await callback.message.edit_text(
                f"✅ Неделя выбрана: {format_week_display(week_number, year)}\n\n"
                f"Теперь отправьте детали активности в формате:\n\n"
                f"<code>/set_activity_for_{year}_{week_number} Название | Описание | Дата | Время</code>\n\n"
                f"<b>Пример:</b>\n"
                f"<code>/set_activity_for_{year}_{week_number} Игра в мафию | Играем в кафе Пушкин | 15.01.2026 | 19:30</code>\n\n"
                f"Поддерживаемые форматы даты: 15.01.2026, 15.01\n"
                f"Поддерживаемые форматы времени: 19:30, 19-30",
                parse_mode="HTML",
            )

            logger.info(
                f"Activity form prompted for week {week_number}/{year}, user {callback.from_user.id} "
                f"in group {callback.message.chat.id}"
            )

    except Exception as e:
        logger.error(f"Error handling set_activity_week callback: {e}", exc_info=True)
        if callback.message and isinstance(callback.message, Message):
            await callback.message.edit_text("❌ Произошла ошибка при обработке выбора недели.")
        if callback.message and isinstance(callback.message, Message):
            await callback.message.edit_text("❌ Произошла ошибка при назначении дежурного.")
