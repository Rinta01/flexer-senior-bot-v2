"""Force pick duty command handler."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from src.database.engine import db_manager
from src.database.models import DutyPool, TelegramUser
from src.database.repositories import (
    DutyRepository,
    PoolRepository,
    UserRepository,
    UserPoolRepository,
)
from src.handlers.activity import get_week_statuses
from src.keyboards.force_pick import create_force_pick_user_keyboard, format_force_pick_user_name
from src.keyboards.week_selector import create_week_selector_keyboard
from src.services.user_manager import UserManager
from src.utils.logger import setup_logging

logger = setup_logging(__name__)

router = Router()


@router.message(Command("force_pick"))
async def force_pick_command(message: Message) -> None:
    """
    Handle /force_pick command - manually assign duty to specific user for a week.

    Usage:
    - /force_pick to select a user from the pool
    - /force_pick @username as a shortcut
    """
    try:
        if not message.chat.id or message.chat.id > 0:
            await message.answer("⚠️ Эта команда работает только в групповых чатах!")
            return

        if not message.text:
            await message.answer("❌ Ошибка: текст команды отсутствует.")
            return

        command_parts = message.text.split(maxsplit=1)

        async with db_manager.async_session() as session:
            # Get or create pool for this group
            pool_repo = PoolRepository(session)
            pool = await pool_repo.get_or_create(
                group_id=message.chat.id, group_title=message.chat.title or "Unknown Group"
            )

            if len(command_parts) < 2:
                user_manager = UserManager(session)
                await _answer_user_picker(message, user_manager, pool)
                logger.info(
                    f"Force pick user picker opened in group {message.chat.id} (pool {pool.id})"
                )
                return

            # Extract username (remove @ if present)
            username_arg = command_parts[1].strip()
            if username_arg.startswith("@"):
                username = username_arg[1:]
            else:
                username = username_arg

            if not username:
                await message.answer("❌ Укажите username пользователя после команды.")
                return

            # Find user by username
            user_repo = UserRepository(session)
            target_user = await user_repo.get_by_username(username)

            if not target_user:
                await message.answer(
                    f"❌ Пользователь @{username} не найден в системе.\n\n"
                    f"Можно вызвать /force_pick без username и выбрать участника из списка."
                )
                return

            # Check if user is in the pool
            user_pool_repo = UserPoolRepository(session)
            user_in_pool = await user_pool_repo.get_user_in_pool(pool.id, target_user.user_id)

            if not user_in_pool:
                await message.answer(
                    f"❌ Пользователь @{username} не состоит в пуле дежурных.\n"
                    f"Попросите пользователя выполнить /join.\n\n"
                    f"Можно вызвать /force_pick без username и выбрать участника из списка."
                )
                return

            await _answer_week_picker(message, session, pool, target_user)

            logger.info(
                f"Force pick initiated for user @{username} (ID {target_user.user_id}) "
                f"in group {message.chat.id} (pool {pool.id})"
            )

    except Exception as e:
        logger.error(f"Error in force_pick_command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обработке команды.")


@router.callback_query(F.data.startswith("force_pick_user:"))
async def handle_force_pick_user_callback(callback: CallbackQuery) -> None:
    """Handle user selection for /force_pick."""
    try:
        if (
            not callback.data
            or not callback.message
            or not isinstance(callback.message, Message)
            or not callback.message.chat
        ):
            return

        await callback.answer()

        try:
            user_id = int(callback.data.split(":", maxsplit=1)[1])
        except (IndexError, ValueError):
            await callback.answer("❌ Ошибка: пользователь не указан", show_alert=True)
            return

        async with db_manager.async_session() as session:
            pool_repo = PoolRepository(session)
            pool = await pool_repo.get_or_create(
                group_id=callback.message.chat.id,
                group_title=callback.message.chat.title or "Unknown Group",
            )

            user_repo = UserRepository(session)
            target_user = await user_repo.get_by_id(user_id)
            if not target_user:
                await callback.message.edit_text("❌ Пользователь не найден в системе.")
                return

            user_pool_repo = UserPoolRepository(session)
            user_in_pool = await user_pool_repo.get_user_in_pool(pool.id, target_user.user_id)
            if not user_in_pool:
                await callback.message.edit_text(
                    f"❌ {format_force_pick_user_name(target_user)} больше не состоит в пуле дежурных."
                )
                return

            await _edit_week_picker(callback.message, session, pool, target_user)

    except Exception as e:
        logger.error(f"Error in handle_force_pick_user_callback: {e}", exc_info=True)
        if callback.message and isinstance(callback.message, Message):
            await callback.message.edit_text("❌ Произошла ошибка при выборе пользователя.")


async def _answer_user_picker(
    message: Message,
    user_manager: UserManager,
    pool: DutyPool,
) -> None:
    users = await user_manager.get_pool_users(pool.id)
    if not users:
        await message.answer(
            "❌ В пуле дежурных пока нет участников.\n\n"
            "Используйте /join чтобы присоединиться."
        )
        return

    keyboard = create_force_pick_user_keyboard(users)
    await message.answer(
        "👤 Выберите участника, которого нужно назначить дежурным:\n\n"
        f"Участников в пуле: {len(users)}",
        reply_markup=keyboard,
    )


async def _answer_week_picker(
    message: Message,
    session,
    pool: DutyPool,
    target_user: TelegramUser,
) -> None:
    keyboard = await _create_force_pick_week_keyboard(session, pool, target_user)
    await message.answer(
        "📅 Выберите неделю для назначения дежурства:\n\n"
        f"Участник: {format_force_pick_user_name(target_user)}",
        reply_markup=keyboard,
    )


async def _edit_week_picker(
    message: Message,
    session,
    pool: DutyPool,
    target_user: TelegramUser,
) -> None:
    keyboard = await _create_force_pick_week_keyboard(session, pool, target_user)
    await message.edit_text(
        "📅 Выберите неделю для назначения дежурства:\n\n"
        f"Участник: {format_force_pick_user_name(target_user)}",
        reply_markup=keyboard,
    )


async def _create_force_pick_week_keyboard(session, pool: DutyPool, target_user: TelegramUser):
    duty_repo = DutyRepository(session)
    week_statuses = await get_week_statuses(duty_repo, pool.id, weeks_ahead=4)

    return create_week_selector_keyboard(
        action_prefix="force_pick_week",
        weeks_ahead=4,
        extra_data={"user_id": target_user.user_id},
        week_statuses=week_statuses,
        back_callback_data="force_pick_back_to_users",
        cancel_callback_data="cancel_force_pick",
    )


@router.callback_query(F.data == "force_pick_back_to_users")
async def handle_force_pick_back_to_users(callback: CallbackQuery) -> None:
    """Return from week selection to force-pick user selection."""
    try:
        if (
            not callback.message
            or not isinstance(callback.message, Message)
            or not callback.message.chat
        ):
            return

        await callback.answer()

        async with db_manager.async_session() as session:
            pool_repo = PoolRepository(session)
            pool = await pool_repo.get_or_create(
                group_id=callback.message.chat.id,
                group_title=callback.message.chat.title or "Unknown Group",
            )

            user_manager = UserManager(session)
            users = await user_manager.get_pool_users(pool.id)
            if not users:
                await callback.message.edit_text(
                    "❌ В пуле дежурных пока нет участников.\n\n"
                    "Используйте /join чтобы присоединиться."
                )
                return

            keyboard = create_force_pick_user_keyboard(users)
            await callback.message.edit_text(
                "👤 Выберите участника, которого нужно назначить дежурным:\n\n"
                f"Участников в пуле: {len(users)}",
                reply_markup=keyboard,
            )

    except Exception as e:
        logger.error(f"Error in handle_force_pick_back_to_users: {e}", exc_info=True)
        if callback.message and isinstance(callback.message, Message):
            await callback.message.edit_text("❌ Произошла ошибка при возврате к списку.")
