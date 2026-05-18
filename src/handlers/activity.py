"""Activity management handler - for setting weekly activities by confirmed duty."""

import re
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.database.engine import db_manager
from src.database.models import DutyAssignment, DutyStatus, TelegramUser
from src.database.repositories import DutyRepository, PoolRepository, UserRepository
from src.keyboards.week_selector import create_week_selector_keyboard
from src.states.activity import ActivityStates
from src.utils.calendar import (
    build_activity_description_for_storage,
    build_google_calendar_url,
    extract_location_from_description,
)
from src.utils.formatters import format_duty_status, format_user_mention, get_week_date_range
from src.utils.logger import setup_logging

logger = setup_logging(__name__)

router = Router()

CHAT_TIMEZONE = timezone(timedelta(hours=3), "UTC+03:00")


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
        activity_description, activity_location = extract_location_from_description(
            duty.activity_description
        )
        activity_time = ""
        if duty.activity_datetime:
            activity_time = duty.activity_datetime.strftime("%d.%m.%Y в %H:%M")

        response += (
            f"\n\n📅 <b>Активность недели:</b>\n" f"<b>Название:</b> {duty.activity_title}\n"
        )

        if activity_description:
            response += f"<b>Описание:</b> {activity_description}\n"

        if activity_location:
            response += f"<b>Место:</b> {activity_location}\n"

        if activity_time:
            response += f"<b>Когда:</b> {activity_time}\n"

        response += f"\nДо встречи, не теряемся 💪"

    else:
        # Activity not set
        response += f"\n\n❓ Активность пока не установлена."

        if duty.status == DutyStatus.CONFIRMED:
            response += (
                f"\n\n💡 {mention}, вы можете добавить информацию о мероприятии:\n"
                f"Используйте <code>/set_activity</code> и пришлите данные ответным сообщением на сообщение бота."
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
            hour=parsed_time.hour,
            minute=parsed_time.minute,
            tzinfo=CHAT_TIMEZONE,
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
    lines = [line for line in lines if not is_activity_placeholder_line(line)]

    if not lines:
        return None

    labeled_result = parse_labeled_activity_lines(lines)
    if labeled_result:
        return labeled_result

    positional_result = parse_positional_activity_lines(lines)
    if positional_result:
        return positional_result

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


def parse_positional_activity_lines(lines: list[str]) -> tuple[str, str, str, str] | None:
    """Parse strict one-line-per-field activity format.

    Line 1: title
    Line 2: description
    Line 3: location
    Line 4: date/time
    """
    if len(lines) < 4:
        return None

    title = lines[0]
    description = lines[1]
    location = lines[2]
    datetime_line = lines[3]

    date_pattern = r"\d{1,2}[.\-]\d{1,2}(?:[.\-]\d{0,4})?"
    time_pattern = r"\d{1,2}[:\-]\d{2}"

    date_match = re.search(date_pattern, datetime_line)
    time_match = re.search(time_pattern, datetime_line)

    date_str = date_match.group(0) if date_match else ""
    time_str = time_match.group(0) if time_match else ""

    if location:
        description = f"{description}\nМесто: {location}".strip()

    return (title, description, date_str, time_str)


def is_activity_placeholder_line(line: str) -> bool:
    """Return True for prompt placeholder lines that should not become activity data."""
    normalized = line.strip().lower()
    return normalized in {
        "название",
        "описание (необязательно)",
        "место",
        "место проведения",
        "место: адрес или место встречи (необязательно)",
        "адрес или место встречи (необязательно)",
        "дата",
        "время",
        "дата и время",
        "28.01 19:00 (необязательно)",
    }


def parse_labeled_activity_lines(lines: list[str]) -> tuple[str, str, str, str] | None:
    """Parse activity lines with labels like 'Название:', 'Дата:', 'Время:'."""
    title = ""
    description_lines = []
    date_str = ""
    time_str = ""
    location = ""
    found_label = False

    date_pattern = r"\d{1,2}[.\-]\d{1,2}(?:[.\-]\d{2,4})?"
    time_pattern = r"\d{1,2}[:\-]\d{2}"
    label_pattern = re.compile(
        r"^(название|описание|место(?:\s+проведения)?|локация|где(?:\s+встречаемся)?|адрес|дата|время|когда)(?:\s*[:\-–—]\s*|\s+)(.*)$",
        re.I,
    )

    for line in lines:
        match = label_pattern.match(line)
        if not match:
            description_lines.append(line)
            continue

        found_label = True
        key = match.group(1).lower()
        value = match.group(2).strip()

        if not value or is_activity_placeholder_line(value):
            continue

        if key == "название":
            title = value
        elif key == "описание":
            description_lines.append(value)
        elif key.startswith("место") or key.startswith("где") or key in {"локация", "адрес"}:
            location = value
        elif key == "дата":
            date_match = re.search(date_pattern, value)
            if date_match:
                date_str = date_match.group(0)
            time_match = re.search(time_pattern, value)
            if time_match:
                time_str = time_match.group(0)
        elif key == "время":
            time_match = re.search(time_pattern, value)
            if time_match:
                time_str = time_match.group(0)
        elif key == "когда":
            date_match = re.search(date_pattern, value)
            time_match = re.search(time_pattern, value)
            if date_match:
                date_str = date_match.group(0)
            if time_match:
                time_str = time_match.group(0)

    if not found_label:
        return None

    description = "\n".join(line for line in description_lines if line.strip())
    if location:
        description = f"{description}\nМесто: {location}".strip()

    return (title or "Активность недели", description, date_str, time_str)


def extract_activity_location(description: str) -> tuple[str, str]:
    """Extract optional location from description lines.

    Supported labels: "Место:", "Локация:", "Где:", "Адрес:".
    Returns a tuple of (clean_description, location).
    """
    if not description:
        return "", ""

    location = ""
    clean_lines = []
    location_pattern = re.compile(
        r"^(?:место(?:\s+проведения)?|локация|где(?:\s+встречаемся)?|адрес)(?:\s*[:\-–—]\s*|\s+)(.+)$",
        re.I,
    )

    for line in description.splitlines():
        match = location_pattern.match(line.strip())
        if match and not location:
            location = match.group(1).strip()
        else:
            clean_lines.append(line)

    return "\n".join(clean_lines).strip(), location


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


def build_calendar_links_keyboard(
    duty: DutyAssignment,
    title: str,
    description: str | None,
    activity_datetime: datetime | None,
    location: str | None,
    user: TelegramUser | None,
) -> InlineKeyboardMarkup | None:
    """Build calendar link buttons for an activity."""
    if not activity_datetime:
        return None

    google_button = InlineKeyboardButton(
        text="🗓 Добавить в Google Calendar",
        url=build_google_calendar_url(
            title=title,
            description=description,
            activity_datetime=activity_datetime,
            location=location,
            user=user,
            duty=duty,
        ),
    )
    return InlineKeyboardMarkup(inline_keyboard=[[google_button]])


@router.message(
    StateFilter(ActivityStates.waiting_for_activity),
    F.chat.type.in_({"group", "supergroup"}),
    F.text,
)
async def handle_activity_input(message: Message, state: FSMContext) -> None:
    """
    Handle activity input when user replies to the prompt message.

    This handler requires the user to reply to the bot's prompt message.
    """
    if not message.text or not message.from_user or not message.chat:
        return

    try:
        # Get saved state data
        data = await state.get_data()
        year = data.get("year")
        week_number = data.get("week_number")
        duty_id = data.get("duty_id")
        chat_id = data.get("chat_id")
        prompt_message_id = data.get("prompt_message_id")
        expected_user_id = data.get("user_id")

        # Validate we have all required data
        if not all([year, week_number, duty_id, chat_id, prompt_message_id]):
            await message.answer(
                "❌ Ошибка: данные о выбранной неделе утеряны. Попробуйте /set_activity снова."
            )
            await state.clear()
            return

        # Type check for duty_id to satisfy type checker
        if not isinstance(duty_id, int):
            await message.answer(
                "❌ Ошибка: некорректный идентификатор дежурства. Попробуйте /set_activity снова."
            )
            await state.clear()
            return

        # Check if user is the one who initiated the command
        if message.from_user.id != expected_user_id:
            # Ignore messages from other users silently
            return

        # Check if this is a reply to the prompt message
        if not message.reply_to_message or message.reply_to_message.message_id != prompt_message_id:
            await message.answer(
                "❌ Пожалуйста, ответьте на детали активности ответным сообщением",
                reply_to_message_id=prompt_message_id,
            )
            return

        # Parse activity details
        parsed = parse_activity_multiline(message.text)

        if not parsed:
            parsed = ("Активность недели", "", "", "")

        title, description, date_str, time_str = parsed
        title = title.strip() if title.strip() else "Активность недели"
        description, location = extract_activity_location(description)

        # Parse date and time if provided
        activity_datetime = None
        datetime_parse_failed = False
        if date_str and time_str:
            activity_datetime = parse_datetime(date_str, time_str)
            if not activity_datetime:
                datetime_parse_failed = True
        elif date_str or time_str:
            datetime_parse_failed = True

        async with db_manager.async_session() as session:
            duty_repo = DutyRepository(session)
            user_repo = UserRepository(session)
            storage_description = build_activity_description_for_storage(description, location)

            # Update activity
            updated_duty = await duty_repo.update_activity(
                duty_id=duty_id,
                title=title,
                description=storage_description,
                activity_datetime=activity_datetime,
            )

            if updated_duty:
                user = await user_repo.get_by_id(updated_duty.user_id)
                # Build response message
                response_parts = [
                    f"✅ <b>Активность на неделю {week_number} установлена!</b>\n",
                    f"🎯 <b>{title}</b>",
                ]

                if description:
                    response_parts.append(f"\n\n📝 <b>Описание:</b>\n{description}")

                if location:
                    response_parts.append(f"\n\n📍 <b>Место:</b> {location}")

                if activity_datetime:
                    formatted_datetime = activity_datetime.strftime("%d.%m.%Y в %H:%M")
                    response_parts.append(f"\n\n📅 <b>Дата и время:</b> {formatted_datetime}")
                else:
                    formatted_datetime = "не указано"
                    if datetime_parse_failed:
                        response_parts.append(
                            "\n\n⚠️ Дату или время не удалось распознать, "
                            "поэтому ссылка на Google Calendar не создана."
                        )

                response_parts.append(f"\n\nУстановлено: {message.from_user.first_name}")

                response = "".join(response_parts)
                calendar_keyboard = build_calendar_links_keyboard(
                    duty=updated_duty,
                    title=title,
                    description=description or None,
                    activity_datetime=activity_datetime,
                    location=location or None,
                    user=user,
                )

                await message.answer(
                    response,
                    parse_mode="HTML",
                    reply_to_message_id=message.message_id,
                    reply_markup=calendar_keyboard if calendar_keyboard else None,
                )
                logger.info(
                    f"Activity set by user {message.from_user.id} for duty {duty_id} "
                    f"(week {week_number}/{year}): {title}, datetime: {formatted_datetime}, "
                    f"location: {location or 'not specified'}"
                )

                # Clear state
                await state.clear()
            else:
                await message.answer(
                    "❌ Не удалось установить активность. Попробуйте позже.",
                    reply_to_message_id=message.message_id,
                )

    except Exception as e:
        logger.error(f"Error in handle_activity_input: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при установке активности.",
            reply_to_message_id=message.message_id if message.message_id else None,
        )
        await state.clear()
