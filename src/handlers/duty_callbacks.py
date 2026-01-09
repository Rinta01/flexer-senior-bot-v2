"""Callback handlers for duty confirmation."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from src.database.engine import db_manager
from src.database.models import DutyStatus
from src.database.repositories import DutyRepository, UserRepository
from src.services.notification import get_week_date_range
from src.utils.logger import setup_logging
from src.utils.validators import format_user_mention

logger = setup_logging(__name__)

router = Router()


@router.callback_query(F.data.startswith("duty_confirm:"))
async def duty_confirm_callback(callback: CallbackQuery) -> None:
    """Handle duty confirmation button."""
    try:
        # Parse callback data: duty_confirm:assignment_id:user_id
        if not callback.data:
            await callback.answer("❌ Неверные данные", show_alert=True)
            return
        _, assignment_id_str, user_id_str = callback.data.split(":")
        assignment_id = int(assignment_id_str)
        expected_user_id = int(user_id_str)

        # Verify that the person clicking is the assigned user
        if callback.from_user.id != expected_user_id:
            await callback.answer(
                "⚠️ Только назначенный дежурный может подтвердить или отказаться!", show_alert=True
            )
            return

        async with db_manager.async_session() as session:
            duty_repo = DutyRepository(session)
            user_repo = UserRepository(session)

            # Get duty assignment
            duty = await duty_repo.get_by_id(assignment_id)
            if not duty:
                await callback.answer("❌ Назначение не найдено", show_alert=True)
                return

            # Check if already processed
            if duty.status != DutyStatus.PENDING:
                await callback.answer(
                    f"ℹ️ Это назначение уже обработано (статус: {duty.status.value})",
                    show_alert=True,
                )
                return

            # Update status to confirmed
            await duty_repo.update_status(assignment_id, DutyStatus.CONFIRMED)

            # Get user info
            user = await user_repo.get_by_id(duty.user_id)
            mention = format_user_mention(duty.user_id, user.username if user else None)

            # Update message
            date_range = get_week_date_range(duty.week_number)
            new_text = (
                f"🎯 <b>Дежурный на неделю {date_range}</b>\n\n"
                f"{mention} принял дежурство! ✅\n\n"
                f"Отвечает за организацию мероприятия на эту неделю.\n\n"
                f"Удачи! 💪"
            )

            if callback.message and isinstance(callback.message, Message):
                await callback.message.edit_text(
                    text=new_text, parse_mode="HTML", reply_markup=None  # Remove buttons
                )

            await callback.answer("✅ Дежурство подтверждено!")
            logger.info(f"User {duty.user_id} confirmed duty assignment {assignment_id}")

    except Exception as e:
        logger.error(f"Error in duty_confirm_callback: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("duty_decline:"))
async def duty_decline_callback(callback: CallbackQuery) -> None:
    """Handle duty decline button."""
    try:
        # Parse callback data: duty_decline:assignment_id:user_id
        if not callback.data:
            await callback.answer("❌ Неверные данные", show_alert=True)
            return
        _, assignment_id_str, user_id_str = callback.data.split(":")
        assignment_id = int(assignment_id_str)
        expected_user_id = int(user_id_str)

        # Verify that the person clicking is the assigned user
        if callback.from_user.id != expected_user_id:
            await callback.answer(
                "⚠️ Только назначенный дежурный может подтвердить или отказаться!", show_alert=True
            )
            return

        async with db_manager.async_session() as session:
            duty_repo = DutyRepository(session)
            user_repo = UserRepository(session)

            # Get duty assignment
            duty = await duty_repo.get_by_id(assignment_id)
            if not duty:
                await callback.answer("❌ Назначение не найдено", show_alert=True)
                return

            # Check if already processed
            if duty.status != DutyStatus.PENDING:
                await callback.answer(
                    f"ℹ️ Это назначение уже обработано (статус: {duty.status.value})",
                    show_alert=True,
                )
                return

            # Update status to skipped (user declined)
            await duty_repo.update_status(assignment_id, DutyStatus.SKIPPED)

            # Get user info
            user = await user_repo.get_by_id(duty.user_id)
            mention = format_user_mention(duty.user_id, user.username if user else None)

            # Update message
            date_range = get_week_date_range(duty.week_number)
            new_text = (
                f"🎯 <b>Дежурный на неделю {date_range}</b>\n\n"
                f"{mention} отказался от дежурства ❌\n\n"
                f"Дежурство будет пропущено.\n\n"
                f"<i>В будущем будет реализован автоматический выбор следующего дежурного.</i>"
            )

            if callback.message and isinstance(callback.message, Message):
                await callback.message.edit_text(
                    text=new_text, parse_mode="HTML", reply_markup=None  # Remove buttons
                )

            await callback.answer("❌ Вы отказались от дежурства")
            logger.info(f"User {duty.user_id} declined duty assignment {assignment_id}")

    except Exception as e:
        logger.error(f"Error in duty_decline_callback: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)
