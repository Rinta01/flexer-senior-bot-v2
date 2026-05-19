"""Auto-pick scheduler control command handler."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.database.engine import db_manager
from src.database.repositories import PoolRepository
from src.utils.logger import setup_logging

logger = setup_logging(__name__)

router = Router()

ENABLE_VALUES = {"on", "enable", "enabled", "true", "1", "yes", "да", "вкл", "включить"}
DISABLE_VALUES = {"off", "disable", "disabled", "false", "0", "no", "нет", "выкл", "отключить"}


@router.message(Command("auto_pick"))
async def auto_pick_command(message: Message) -> None:
    """Handle /auto_pick command - show or change auto-pick state for this group."""
    try:
        if not message.chat.id or message.chat.id > 0:
            await message.answer("⚠️ Эта команда работает только в групповых чатах!")
            return

        command_parts = (message.text or "").split(maxsplit=1)
        requested_state = _parse_requested_state(command_parts[1] if len(command_parts) > 1 else "")

        if len(command_parts) > 1 and requested_state is None:
            await message.answer(
                "❌ Не понял значение.\n\n"
                "Используйте:\n"
                "<code>/auto_pick</code> — показать текущий статус\n"
                "<code>/auto_pick on</code> — включить авто-выбор\n"
                "<code>/auto_pick off</code> — выключить авто-выбор",
                parse_mode="HTML",
            )
            return

        async with db_manager.async_session() as session:
            pool_repo = PoolRepository(session)
            pool = await pool_repo.get_or_create(
                group_id=message.chat.id,
                group_title=message.chat.title or "Unknown Group",
            )

            if requested_state is None:
                await message.answer(_format_status(pool.auto_pick_enabled))
                return

            pool = await pool_repo.set_auto_pick_enabled(message.chat.id, requested_state)
            if not pool:
                await message.answer("❌ Пул для этой группы не найден.")
                return

            logger.info(
                f"Auto-pick for group {message.chat.id} set to {pool.auto_pick_enabled}"
            )
            await message.answer(_format_update(pool.auto_pick_enabled))

    except Exception as e:
        logger.error(f"Error in auto_pick_command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при изменении настроек авто-выбора.")


def _parse_requested_state(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in ENABLE_VALUES:
        return True
    if normalized in DISABLE_VALUES:
        return False
    return None


def _format_status(enabled: bool) -> str:
    status = "включен ✅" if enabled else "выключен ⏸️"
    return (
        f"⚙️ Автоматический выбор дежурного для этой группы сейчас <b>{status}</b>.\n\n"
        "Изменить:\n"
        "<code>/auto_pick on</code> — включить\n"
        "<code>/auto_pick off</code> — выключить"
    )


def _format_update(enabled: bool) -> str:
    if enabled:
        return "✅ Автоматический выбор дежурного включен для этой группы."
    return "⏸️ Автоматический выбор дежурного выключен для этой группы."
