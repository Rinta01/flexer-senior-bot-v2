"""Activity management handler - for setting weekly activities by confirmed duty."""

from datetime import datetime, date, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.database.engine import db_manager
from src.database.models import DutyStatus
from src.database.repositories import DutyRepository, PoolRepository, UserRepository
from src.services.duty_manager import DutyManager
from src.utils.formatters import get_week_date_range
from src.utils.logger import setup_logging
from src.utils.validators import format_user_mention

logger = setup_logging(__name__)

router = Router()


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


@router.message(Command("set_activity"))
async def set_activity_command(message: Message) -> None:
    """
    Handle /set_activity command - set weekly activity details.

    Format: /set_activity <title> | <description> | <date> | <time>
    Example: /set_activity Игра в мафию | Играем в мафию в кафе | 15.01.2026 | 19:30
    """
    if not message.chat or message.chat.id > 0:
        await message.answer("⚠️ Эта команда работает только в групповых чатах!")
        return

    # Проверяем авторизацию пользователя СРАЗУ
    try:
        async with db_manager.async_session() as session:
            pool_repo = PoolRepository(session)
            duty_repo = DutyRepository(session)

            # Получаем пул для этой группы
            pool = await pool_repo.get_by_id(message.chat.id)
            if not pool:
                await message.answer(
                    "❌ Пул дежурных не найден для этой группы. "
                    "Сначала кто-то должен присоединиться через /join"
                )
                return

            # Получаем текущую неделю
            current_week = date.today().isocalendar()[1]

            # Проверяем, что пользователь - подтвержденный дежурный на этой неделе
            confirmed_duty = await duty_repo.get_current_confirmed_duty(pool.id, current_week)

            if not confirmed_duty:
                await message.answer(
                    "ℹ️ На этой неделе нет подтвержденного дежурного. "
                    "Сначала кто-то должен принять дежурство."
                )
                return

            if not message.from_user or confirmed_duty.user_id != message.from_user.id:
                await message.answer(
                    "❌ Только подтвержденный дежурный текущей недели может устанавливать активность."
                )
                return

    except Exception as e:
        logger.error(f"Error checking authorization in set_activity_command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при проверке авторизации.")
        return

    if not message.text:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "📝 Формат: /set_activity <название> | <описание> | <дата> | <время>\n\n"
            "Пример:\n"
            "<code>/set_activity Игра в мафию | Играем в мафию в кафе Пушкин | 15.01.2026 | 19:30</code>\n\n"
            "Поддерживаемые форматы даты: 15.01.2026, 15.01, 15-01-2026, 15-01\n"
            "Поддерживаемые форматы времени: 19:30, 19-30"
        )
        return

    # Парсим аргументы
    command_text = message.text[len("/set_activity") :].strip()
    if not command_text:
        await message.answer("❌ Введите детали активности после команды.")
        return

    # Разделяем по символу "|"
    parts = [part.strip() for part in command_text.split("|")]
    if len(parts) != 4:
        await message.answer(
            "❌ Неверный формат. Нужно 4 части, разделенные символом |:\n"
            "<code>/set_activity Название | Описание | Дата | Время</code>"
        )
        return

    title, description, date_str, time_str = parts

    if not title or not description or not date_str or not time_str:
        await message.answer("❌ Все поля должны быть заполнены.")
        return

    # Парсим дату и время
    activity_datetime = parse_datetime(date_str, time_str)
    if not activity_datetime:
        await message.answer(
            "❌ Неверный формат даты или времени.\n\n"
            "Поддерживаемые форматы даты: 15.01.2026, 15.01, 15-01-2026, 15-01\n"
            "Поддерживаемые форматы времени: 19:30, 19-30"
        )
        return

    try:
        async with db_manager.async_session() as session:
            duty_repo = DutyRepository(session)

            # Получаем пул для этой группы
            pool = await pool_repo.get_by_id(message.chat.id)

            # Получаем текущую неделю
            current_week = date.today().isocalendar()[1]

            pool = await PoolRepository(session).get_by_id(message.chat.id)
            if not pool:
                await message.answer(
                    "❌ Пул дежурных не найден для этой группы. "
                    "Сначала кто-то должен присоединиться через /join"
                )
                return

            confirmed_duty = await duty_repo.get_current_confirmed_duty(pool.id, current_week)
            if not confirmed_duty:
                await message.answer(
                    "ℹ️ На этой неделе нет подтвержденного дежурного. "
                    "Сначала кто-то должен принять дежурство."
                )
                return

            # Обновляем активность
            updated_duty = await duty_repo.update_activity(
                duty_id=confirmed_duty.id,
                title=title,
                description=description,
                activity_datetime=activity_datetime,
            )

            if updated_duty:
                # Форматируем дату для вывода
                formatted_datetime = activity_datetime.strftime("%d.%m.%Y в %H:%M")

                response = (
                    f"✅ <b>Активность на неделю установлена!</b>\n\n"
                    f"🎯 <b>{title}</b>\n\n"
                    f"📝 <b>Описание:</b>\n{description}\n\n"
                    f"📅 <b>Дата и время:</b> {formatted_datetime}\n\n"
                    f"Установлено дежурным: {message.from_user.first_name}"
                )

                await message.answer(response)

                logger.info(
                    f"Activity set by user {message.from_user.id} for duty {confirmed_duty.id}: "
                    f"{title} on {formatted_datetime}"
                )
            else:
                await message.answer("❌ Не удалось установить активность. Попробуйте позже.")

    except Exception as e:
        logger.error(f"Error in set_activity_command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при установке активности.")


@router.message(Command("activity"))
async def show_activity_command(message: Message) -> None:
    """Handle /activity command - show current duty and activity."""
    if not message.chat or message.chat.id > 0:
        await message.answer("⚠️ Эта команда работает только в групповых чатах!")
        return

    try:
        async with db_manager.async_session() as session:
            pool_repo = PoolRepository(session)
            user_repo = UserRepository(session)
            duty_repo = DutyRepository(session)

            # Получаем пул для этой группы
            pool = await pool_repo.get_by_id(message.chat.id)
            if not pool:
                await message.answer(
                    "❌ Пул дежурных не найден для этой группы. "
                    "Сначала кто-то должен присоединиться через /join"
                )
                return

            # Получаем текущую неделю и дежурного (любого статуса)
            current_week = date.today().isocalendar()[1]
            current_duty_assignment = await duty_repo.get_duty_for_week(pool.id, current_week)

            if not current_duty_assignment:
                await message.answer("ℹ️ На эту неделю дежурный ещё не выбран.")
                return

            # Получаем информацию о пользователе
            user = await user_repo.get_by_id(current_duty_assignment.user_id)
            if not user:
                await message.answer("❌ Не удалось найти информацию о дежурном.")
                return

            mention = format_user_mention(current_duty_assignment.user_id, user.username)

            # Получаем диапазон дат для недели
            date_range = get_week_date_range(current_duty_assignment.week_number)

            # Базовый ответ с информацией о дежурном
            response = (
                f"🎯 <b>Дежурный недели</b>\n\n"
                f"Неделя: {date_range}\n"
                f"Дежурный: {mention}\n"
                f"Статус: {current_duty_assignment.status.value}\n"
            )

            # Пытаемся получить информацию об активности
            if current_duty_assignment.activity_title:
                # Есть установленная активность
                activity_time = ""
                if current_duty_assignment.activity_datetime:
                    activity_time = current_duty_assignment.activity_datetime.strftime(
                        "%d.%m.%Y в %H:%M"
                    )

                response += (
                    f"\n\n📅 <b>Активность недели:</b>\n"
                    f"<b>Название:</b> {current_duty_assignment.activity_title}\n"
                )

                if current_duty_assignment.activity_description:
                    response += f"<b>Описание:</b> {current_duty_assignment.activity_description}\n"

                if activity_time:
                    response += f"<b>Когда:</b> {activity_time}\n"

                response += f"\nУвидимся на мероприятии! 🎉"

            else:
                # Активность не установлена
                response += f"\n\n❓ Активность пока не установлена."

                if current_duty_assignment.status == DutyStatus.CONFIRMED:
                    response += (
                        f"\n\n💡 {mention}, вы можете добавить информацию о мероприятии:\n"
                        f"<code>/set_activity Название | Описание | Дата | Время</code>"
                    )
                else:
                    response += f"\n\n⏳ Ожидаем подтверждения от дежурного."

            await message.answer(response, parse_mode="HTML")
            logger.info(f"Handled /activity in group {message.chat.id}")

    except Exception as e:
        logger.error(f"Error in show_activity_command: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при получении информации об активности.")
