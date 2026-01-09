"""Pool list command handler."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.database.engine import db_manager
from src.database.models import DutyStatus
from src.database.repositories import PoolRepository
from src.services.user_manager import UserManager
from src.utils.logger import setup_logging
from src.utils.validators import format_user_mention

logger = setup_logging(__name__)

router = Router()


@router.message(Command("pool"))
async def pool_command(message: Message) -> None:
    """Handle /pool command - show all users in pool."""
    if not message.chat or message.chat.type == "private":
        await message.answer("❌ Эта команда работает только в группах.")
        return

    try:
        async with (
            db_manager.async_session() as session  # pyright: ignore[reportGeneralTypeIssues]
        ):
            pool_repo = PoolRepository(session)
            user_manager = UserManager(session)

            # Get or create pool for this group
            pool = await pool_repo.get_or_create(
                group_id=message.chat.id, group_title=message.chat.title or "Unknown Group"
            )

            logger.info(f"Getting users for pool {pool.id} (group {message.chat.id})")

            # Get all users in pool
            users = await user_manager.get_pool_users(pool.id)

            logger.info(f"Found {len(users)} users in pool")

            if not users:
                await message.answer(
                    "📋 <b>Пул дежурных пуст</b>\n\n" "Используйте /join чтобы присоединиться!"
                )
                return

            # Format user list
            user_list = []
            for idx, user in enumerate(users, 1):
                # Format username
                username_part = f"@{user['username']}" if user["username"] else ""
                full_name = user["first_name"]
                if user["last_name"]:
                    full_name += f" {user['last_name']}"

                # Determine status emoji based on duty status
                duty_status = user.get("duty_status")

                if duty_status == DutyStatus.CONFIRMED:
                    status = "✅ (дежурный на этой неделе)"
                elif duty_status == DutyStatus.PENDING:
                    status = "⏱️ (ожидает подтверждения)"
                elif duty_status in (DutyStatus.DECLINED, DutyStatus.SKIPPED):
                    status = "❌ (отказался)"
                elif user["completed_cycle"]:
                    status = "✅ (завершил цикл)"
                else:
                    status = "⏳ (ожидает очереди)"

                # Format line
                if username_part:
                    user_list.append(f"{idx}. {full_name} ({username_part}) {status}")
                else:
                    user_list.append(f"{idx}. {full_name} {status}")

            response = (
                f"📋 <b>Участники пула ({len(users)})</b>\n\n"
                + "\n".join(user_list)
                + "\n\n"
                + "<b>Статусы:</b>\n"
                + "✅ = дежурный/завершил цикл\n"
                + "⏱️ = ожидает подтверждения дежурства\n"
                + "❌ = отказался от дежурства\n"
                + "⏳ = ожидает своей очереди"
            )

            await message.answer(response)

    except Exception as e:
        logger.error(f"Error in pool command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при получении списка участников.")
