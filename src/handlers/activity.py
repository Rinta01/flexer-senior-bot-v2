"""Activity management handler - for setting weekly activities by confirmed duty."""

import re
from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.database.engine import db_manager
from src.database.models import DutyAssignment, DutyStatus, TelegramUser
from src.database.repositories import DutyRepository, PoolRepository
from src.keyboards.week_selector import create_week_selector_keyboard
from src.utils.formatters import format_duty_status, format_user_mention, get_week_date_range
from src.utils.logger import setup_logging

logger = setup_logging(__name__)

router = Router()


def format_activity_info(duty: DutyAssignment, user: TelegramUser) -> str:
    """
    Format activity information message for display.

    This is a pure function that can be tested independently.

    Args:
        duty: DutyAssignment object with all duty information
        user: TelegramUser object for the assigned user

    Returns:
        Formatted HTML string with duty and activity information
    """
    # Format mention using centralized helper with first_name fallback
    mention = format_user_mention(duty.user_id, user.username, user.first_name)

    date_range = get_week_date_range(duty.week_number)

    # Base response with duty info (use formatted status with Russian text)
    status_display = format_duty_status(duty.status)
    response = (
        f"🎯 <b>Дежурный недели</b>\n\n"
        f"Неделя: {date_range}\n"
        f"Дежурный: {mention}\n"
        f"Статус: {status_display}\n"
    )

    # Add activity info if set
    if duty.activity_title:
        activity_time = ""
        if duty.activity_datetime:
            activity_time = duty.activity_datetime.strftime("%d.%m.%Y в %H:%M")

        response += (
            f"\n\n📅 <b>Активность недели:</b>\n" f"<b>Название:</b> {duty.activity_title}\n"
        )

        if duty.activity_description:
            response += f"<b>Описание:</b> {duty.activity_description}\n"

        if activity_time:
            response += f"<b>Когда:</b> {activity_time}\n"

        response += f"\nДо встречи, не теряемся 💪"

    else:
        # Activity not set
        response += f"\n\n❓ Активность пока не установлена."

        if duty.status == DutyStatus.CONFIRMED:
            response += (
                f"\n\n💡 {mention}, вы можете добавить информацию о мероприятии:\n"
                f"<code>/set_activity</code>\n"
                f"Затем введите название, описание и дату/время."
            )
        elif duty.status == DutyStatus.PENDING:
            response += f"\n\n⏳ Ожидаем подтверждения от дежурного."
        elif duty.status == DutyStatus.SKIPPED:
            response += f"\n\n❌ Дежурный отказался от дежурства на эту неделю."

    return response


def parse_datetime(date_str: str, time_str: str) -> datetime | None:
    """Parse date and time strings into datetime object."""
    try:
        # Поддерживаемые форматы дат
        date_formats = [
            "%d.%m.%Y",  # 15.01.2026
            "%d.%m",  # 15.01 (текущий год)
            "%d-%m-%Y",  # 15-01-2026
            "%d-%m",  # 15-01 (текущий год)
        ]

        # Поддерживаемые форматы времени
        time_formats = [
            "%H:%M",  # 19:30
            "%H-%M",  # 19-30
        ]

        parsed_date = None
        for date_format in date_formats:
            try:
                if "%Y" not in date_format:
                    # Добавляем текущий год
                    date_str_with_year = f"{date_str}.{datetime.now().year}"
                    parsed_date = datetime.strptime(date_str_with_year, date_format + ".%Y")
                else:
                    parsed_date = datetime.strptime(date_str, date_format)
                break
            except ValueError:
                continue

        if not parsed_date:
            return None

        parsed_time = None
        for time_format in time_formats:
            try:
                time_obj = datetime.strptime(time_str, time_format).time()
                parsed_time = time_obj
                break
            except ValueError:
                continue

        if not parsed_time:
            return None

        # Объединяем дату и время и добавляем timezone
        combined_datetime = parsed_date.replace(
            hour=parsed_time.hour, minute=parsed_time.minute, tzinfo=timezone.utc
        )
        return combined_datetime

    except Exception:
        return None


async def get_week_statuses(
    duty_repo: DutyRepository, pool_id: int, weeks_ahead: int = 4
) -> dict[tuple[int, int], dict[str, bool]]:
    """
    Get status indicators for weeks (duty assigned, activity set).

    Args:
        duty_repo: DutyRepository instance
        pool_id: Pool ID to check duties for
        weeks_ahead: Number of weeks ahead to check (default: 4)

    Returns:
        Dictionary mapping (year, week_number) to status dict with has_duty and has_activity flags
    """
    current_date = datetime.now()
    current_week = current_date.isocalendar()[1]
    current_year = current_date.year

    week_statuses = {}
    for i in range(weeks_ahead + 1):  # Current + N weeks ahead
        week_num = current_week + i
        year = current_year
        if week_num > 52:
            week_num = week_num - 52
            year = current_year + 1

        duty = await duty_repo.get_duty_for_week(pool_id, year, week_num)
        # Don't show duty indicator if duty was declined (SKIPPED)
        has_active_duty = duty is not None and duty.status != DutyStatus.SKIPPED
        week_statuses[(year, week_num)] = {
            "has_duty": has_active_duty,
            "has_activity": duty is not None
            and has_active_duty
            and duty.activity_title is not None,
        }

    return week_statuses


@router.message(Command("set_activity"))
async def set_activity_command(message: Message) -> None:
    """
    Handle /set_activity command - shows week selection for setting activity.

    User will be prompted to enter activity details after selecting a week.
    """
    if not message.chat or message.chat.id > 0:
        await message.answer("⚠️ Эта команда работает только в групповых чатах!")
        return

    try:
        async with db_manager.async_session() as session:
            pool_repo = PoolRepository(session)

            # Получаем пул для этой группы
            pool = await pool_repo.get_by_id(message.chat.id)
            if not pool:
                await message.answer(
                    "❌ Пул дежурных не найден для этой группы. "
                    "Сначала кто-то должен присоединиться через /join"
                )
                return

            # Get week statuses for indicators
            duty_repo = DutyRepository(session)
            week_statuses = await get_week_statuses(duty_repo, pool.id, weeks_ahead=4)

            # Показываем клавиатуру выбора недели
            keyboard = create_week_selector_keyboard(
                action_prefix="set_activity_week",
                weeks_ahead=4,
                extra_data={"user_id": str(message.from_user.id if message.from_user else "0")},
                week_statuses=week_statuses,
            )

            await message.answer(
                "📅 Выберите неделю для установки активности:\n\n"
                "После выбора недели вы сможете ввести детали мероприятия.",
                reply_markup=keyboard,
            )

            logger.info(
                f"Set activity week selection shown for user {message.from_user.id if message.from_user else 'unknown'} "
                f"in group {message.chat.id}"
            )

    except Exception as e:
        logger.error(f"Error in set_activity_command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обработке команды.")


@router.message(Command("activity"))
async def show_activity_command(message: Message) -> None:
    """Handle /activity command - show duty and activity for a selected week."""
    if not message.chat or message.chat.id > 0:
        await message.answer("⚠️ Эта команда работает только в групповых чатах!")
        return

    try:
        async with db_manager.async_session() as session:
            pool_repo = PoolRepository(session)

            # Получаем пул для этой группы
            pool = await pool_repo.get_by_id(message.chat.id)
            if not pool:
                await message.answer(
                    "❌ Пул дежурных не найден для этой группы. "
                    "Сначала кто-то должен присоединиться через /join"
                )
                return

            # Get week statuses for indicators
            duty_repo = DutyRepository(session)
            week_statuses = await get_week_statuses(duty_repo, pool.id, weeks_ahead=4)

            # Показываем клавиатуру выбора недели
            keyboard = create_week_selector_keyboard(
                action_prefix="activity_week", weeks_ahead=4, week_statuses=week_statuses
            )

            await message.answer(
                "📅 Выберите неделю для просмотра дежурного и активности:", reply_markup=keyboard
            )

            logger.info(f"Activity week selection shown in group {message.chat.id}")

    except Exception as e:
        logger.error(f"Error in show_activity_command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обработке команды.")


def parse_activity_multiline(text: str) -> tuple[str, str, str, str] | None:
    """
    Parse activity input from multiline format.

    Format:
    Line 1: Title (required)
    Lines 2-N-1: Description (optional, everything between title and date)
    Last line: Date Time (optional, must contain date pattern)

    Examples:
        "Боулинг"
        ->  ("Боулинг", "", "", "")

        "Боулинг
        Идём играть в боулинг на Невском"
        -> ("Боулинг", "Идём играть в боулинг на Невском", "", "")

        "Боулинг
        Идём играть в боулинг на Невском
        28.01 19:00"
        -> ("Боулинг", "Идём играть в боулинг на Невском", "28.01", "19:00")

    Args:
        text: Multiline input string

    Returns:
        Tuple of (title, description, date_str, time_str) or None if invalid
    """
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]

    if not lines:
        return None

    # First line is always title
    title = lines[0]

    if len(lines) == 1:
        # Only title provided
        return (title, "", "", "")

    # Try to find date/time in last line
    last_line = lines[-1]
    date_pattern = r"\d{1,2}\.\d{1,2}\.?\d{0,4}"  # Matches: 28.01, 28.01.2026
    time_pattern = r"\d{1,2}[:\-]\d{2}"  # Matches: 19:00, 19-30

    has_date = re.search(date_pattern, last_line)
    has_time = re.search(time_pattern, last_line)

    if has_date or has_time:
        # Last line contains date/time
        description_lines = lines[1:-1]
        description = "\n".join(description_lines) if description_lines else ""

        # Extract date and time from last line
        date_str = has_date.group(0) if has_date else ""
        time_str = has_time.group(0) if has_time else ""

        return (title, description, date_str, time_str)
    else:
        # Last line is part of description, no date/time
        description = "\n".join(lines[1:])
        return (title, description, "", "")


def validate_duty_permissions(duty: DutyAssignment, user_id: int) -> bool:
    """
    Check if user can set activity for this duty.

    Args:
        duty: Duty assignment to check
        user_id: Telegram user ID

    Returns:
        True if user has permission, False otherwise
    """
    return duty.user_id == user_id and duty.status == DutyStatus.CONFIRMED


@router.message(lambda message: message.text and message.text.startswith("/set_activity_for_"))
async def set_activity_for_week_command(message: Message) -> None:
    """
    Handle /set_activity_for_{year}_{week} command - set activity details for specific week.

    Format: /set_activity_for_2026_4 <title> | <description> | <date> | <time>
    """
    if not message.chat or message.chat.id > 0 or not message.text or not message.from_user:
        return

    try:
        # Parse year and week from command
        command_parts = message.text.split()[0].split("_")
        if len(command_parts) < 5:
            await message.answer("❌ Неверный формат команды.")
            return

        year = int(command_parts[3])
        week_number = int(command_parts[4])

        # Parse activity details
        command_text = (
            message.text[message.text.find(" ") + 1 :].strip() if " " in message.text else ""
        )
        if not command_text:
            await message.answer(
                "❌ Введите детали активности после команды.\n\n"
                "📝 <b>Формат:</b>\n"
                f"<code>/set_activity_for_{year}_{week_number}\n"
                "Название\n"
                "Описание (необязательно)\n"
                "28.01 19:00 (необязательно)</code>\n\n"
                "💡 Описание, дата и время необязательны!",
                parse_mode="HTML",
            )
            return

        # Parse multiline format
        parsed = parse_activity_multiline(command_text)

        if not parsed:
            await message.answer(
                "❌ Неверный формат.\n\n"
                "📝 <b>Формат:</b>\n"
                "<code>Название\n"
                "Описание (необязательно)\n"
                "28.01 19:00 (необязательно)</code>\n\n"
                "💡 Минимум нужно указать название активности!",
                parse_mode="HTML",
            )
            return

        title, description, date_str, time_str = parsed

        # Parse date and time if provided
        activity_datetime = None
        if date_str and time_str:
            activity_datetime = parse_datetime(date_str, time_str)
            if not activity_datetime:
                await message.answer(
                    "❌ Неверный формат даты или времени.\n\n"
                    "Поддерживаемые форматы даты: 15.01.2026, 15.01\n"
                    "Поддерживаемые форматы времени: 19:30, 19-30"
                )
                return

        async with db_manager.async_session() as session:
            pool_repo = PoolRepository(session)
            duty_repo = DutyRepository(session)

            # Get pool
            pool = await pool_repo.get_by_id(message.chat.id)
            if not pool:
                await message.answer("❌ Пул дежурных не найден.")
                return

            # Get duty for the week
            duty_assignment = await duty_repo.get_duty_for_week(
                pool_id=pool.id, year=year, week_number=week_number
            )

            if not duty_assignment:
                await message.answer(f"❌ Дежурный на неделю {week_number}/{year} не найден.")
                return

            if duty_assignment.status != DutyStatus.CONFIRMED:
                await message.answer("❌ Дежурство ещё не подтверждено.")
                return

            # Update activity
            updated_duty = await duty_repo.update_activity(
                duty_id=duty_assignment.id,
                title=title,
                description=description if description else None,
                activity_datetime=activity_datetime,
            )

            if updated_duty:
                # Build response message
                response_parts = [
                    f"✅ <b>Активность на неделю {week_number} установлена!</b>\n",
                    f"🎯 <b>{title}</b>",
                ]

                if description:
                    response_parts.append(f"\n\n📝 <b>Описание:</b>\n{description}")

                if activity_datetime:
                    formatted_datetime = activity_datetime.strftime("%d.%m.%Y в %H:%M")
                    response_parts.append(f"\n\n📅 <b>Дата и время:</b> {formatted_datetime}")
                else:
                    formatted_datetime = "не указано"

                response_parts.append(f"\n\nУстановлено: {message.from_user.first_name}")

                response = "".join(response_parts)

                await message.answer(response, parse_mode="HTML")

                logger.info(
                    f"Activity set by user {message.from_user.id} for duty {duty_assignment.id} "
                    f"(week {week_number}/{year}): {title}, datetime: {formatted_datetime}"
                )
            else:
                await message.answer("❌ Не удалось установить активность. Попробуйте позже.")

    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing set_activity_for_week command: {e}")
        await message.answer("❌ Неверный формат команды.")
    except Exception as e:
        logger.error(f"Error in set_activity_for_week_command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при установке активности.")
