"""Week selection callback handlers."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.database.engine import db_manager
from src.database.models import DutyStatus
from src.database.repositories import (
    DutyRepository,
    PoolRepository,
    UserRepository,
    UserPoolRepository,
)
from src.keyboards.force_pick import format_force_pick_user_name
from src.keyboards.week_selector import format_week_display, parse_week_callback
from src.services.duty_manager import DutyManager
from src.services.notification import NotificationService
from src.states.activity import ActivityStates
from src.utils.formatters import get_week_date_range
from src.utils.logger import setup_logging

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
                status = result.get("status")
                if status == "pending":
                    await callback.message.edit_text(
                        f"ℹ️ На {format_week_display(week_number, year)} уже есть дежурный, ожидающий подтверждения.\n"
                        f"Случайный выбор не может заменить существующего дежурного.\n\n"
                        f"Используйте /force_pick для принудительного назначения."
                    )
                else:
                    await callback.message.edit_text(
                        f"ℹ️ На {format_week_display(week_number, year)} уже назначен дежурный.\n"
                        f"Случайный выбор работает только для недель с отказавшимся дежурным."
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
                message_to_edit=callback.message,
            )

            if success:
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
        user_id_raw = data.get("user_id")
        username = data.get("username")
        force = data.get("force") == "true"  # Convert string "true" to boolean

        if not user_id_raw and not username:
            await callback.answer("❌ Ошибка: пользователь не указан", show_alert=True)
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
            if user_id_raw:
                try:
                    user_id = int(user_id_raw)
                except ValueError:
                    await callback.message.edit_text("❌ Ошибка: некорректный пользователь.")
                    return
                target_user = await user_repo.get_by_id(user_id)
            else:
                target_user = await user_repo.get_by_username(username)

            if not target_user:
                await callback.message.edit_text("❌ Пользователь не найден в системе.")
                return

            user_display = format_force_pick_user_name(target_user)

            user_pool_repo = UserPoolRepository(session)
            user_in_pool = await user_pool_repo.get_user_in_pool(pool.id, target_user.user_id)
            if not user_in_pool:
                await callback.message.edit_text(
                    f"❌ {user_display} больше не состоит в пуле дежурных."
                )
                return

            # Assign duty to user for the week
            duty_manager = DutyManager(session)
            result = await duty_manager.assign_duty_to_user_for_week(
                pool.id, target_user.user_id, year, week_number, force=force
            )

            if not result:
                await callback.message.edit_text(
                    f"❌ Не удалось назначить {user_display} дежурным на {format_week_display(week_number, year)}.\n"
                    f"Возможно, на эту неделю уже есть подтвержденный дежурный."
                )
                return

            # Check if confirmation is needed
            if result.get("needs_confirmation"):
                existing_status = result.get("existing_status", "unknown")
                status_text = {
                    "pending": "ожидает подтверждения",
                    "confirmed": "подтвержден",
                    "skipped": "отказался от дежурства",
                    "declined": "отказался от дежурства",
                    "force_removed": "заменен ранее",
                }.get(existing_status, "неизвестный статус")

                existing_user_display = "текущий дежурный"
                existing_duty = result.get("existing_duty")
                if existing_duty:
                    existing_user = await user_repo.get_by_id(existing_duty.user_id)
                    if existing_user:
                        existing_user_display = format_force_pick_user_name(existing_user)

                builder = InlineKeyboardBuilder()
                builder.button(
                    text="✅ Да, заменить",
                    callback_data=(
                        f"force_pick_week:{year}:{week_number}:"
                        f"user_id:{target_user.user_id}:force:true"
                    ),
                )
                builder.button(
                    text="⬅️ Назад",
                    callback_data=f"force_pick_user:{target_user.user_id}",
                )
                builder.button(text="❌ Отмена", callback_data="cancel_force_pick")
                builder.adjust(1, 2)

                await callback.message.edit_text(
                    f"⚠️ ВНИМАНИЕ!\n\n"
                    f"На {format_week_display(week_number, year)} уже назначен "
                    f"{existing_user_display} ({status_text}).\n\n"
                    f"Заменить его на {user_display}?",
                    reply_markup=builder.as_markup(),
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
                message_to_edit=callback.message,
            )

            if success:
                logger.info(
                    f"Force picked duty for week {week_number}/{year}: user ID {target_user.user_id} "
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
async def handle_set_activity_week_callback(callback: CallbackQuery, state: FSMContext) -> None:
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
                )
                return

            # Prompt user to enter activity details
            prompt_message = await callback.message.edit_text(
                f"✅ Неделя выбрана: {format_week_display(week_number, year)}\n\n"
                f"📝 <b>Ответьте на это сообщение</b> (через Reply) с деталями активности:\n\n"
                f"<b>Формат:</b>\n"
                f"<code>Название\n"
                f"Описание\n"
                f"Место\n"
                f"25.05 16:00</code>\n\n"
                f"<b>Пример:</b>\n"
                f"<code>Лазертаг\n"
                f"Стреляем пау пау\n"
                f"Авиапарк\n"
                f"25.05 16:00</code>\n\n"
                f"💡 Каждое поле максимум в одну строку. Можно пропускать необязательные поля пустой строкой.",
                parse_mode="HTML",
            )

            # Check if edit_text returned a Message (not just True)
            if not isinstance(prompt_message, Message):
                await callback.message.answer("❌ Ошибка при отправке сообщения.")
                return

            # Save week info and message_id to state
            await state.set_state(ActivityStates.waiting_for_activity)
            await state.update_data(
                year=year,
                week_number=week_number,
                duty_id=duty_assignment.id,
                chat_id=callback.message.chat.id,
                prompt_message_id=prompt_message.message_id,
                user_id=callback.from_user.id,
            )

            logger.info(
                f"Activity state set for week {week_number}/{year}, user {callback.from_user.id} "
                f"in group {callback.message.chat.id}"
            )

    except Exception as e:
        logger.error(f"Error handling set_activity_week callback: {e}", exc_info=True)
        if callback.message and isinstance(callback.message, Message):
            await callback.message.edit_text("❌ Произошла ошибка при обработке выбора недели.")


@router.callback_query(F.data == "cancel_force_pick")
async def handle_cancel_force_pick(callback: CallbackQuery) -> None:
    """Handle cancellation of force pick operation."""
    await callback.answer()
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text("❌ Операция отменена.")
