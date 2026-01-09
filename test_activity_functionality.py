#!/usr/bin/env python3
"""Manual test script for activity functionality."""

import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from src.database.engine import db_manager
from src.database.models import DutyAssignment, TelegramUser, DutyPool, DutyStatus
from src.database.repositories import DutyRepository


async def test_activity_functionality():
    """Test activity management functionality."""
    print("🧪 Тестирование функционала управления активностями")

    async with db_manager.async_session() as session:
        # Create test pool and user
        test_pool = DutyPool(group_id=-1, group_title="Test Group", current_cycle=1)
        session.add(test_pool)

        test_user = TelegramUser(
            user_id=-1, username="test_user", first_name="Test", last_name="User", is_active=True
        )
        session.add(test_user)
        await session.commit()  # Commit to get IDs

        # Create test duty assignment
        test_duty = DutyAssignment(
            pool_id=test_pool.id,
            user_id=-1,
            week_number=1,
            assignment_date=datetime.now(timezone.utc),
            cycle_number=1,
            status=DutyStatus.CONFIRMED,
        )
        session.add(test_duty)
        await session.commit()

        duty_repo = DutyRepository(session)

        # Test 1: Get current confirmed duty - check by pool group_id
        print("✅ Тест 1: Получение подтвержденного дежурного")
        confirmed_duty = await duty_repo.get_current_confirmed_duty(-1, -1)
        assert confirmed_duty is not None, "Должен найти подтвержденного дежурного"
        assert confirmed_duty.user_id == -1, "ID пользователя должен совпадать"
        assert confirmed_duty.status == DutyStatus.CONFIRMED, "Статус должен быть CONFIRMED"
        print("   ✓ Подтвержденный дежурный найден корректно")

        # Test 2: Update activity
        print("✅ Тест 2: Обновление активности")
        activity_time = datetime(2024, 1, 15, 19, 0, tzinfo=timezone.utc)
        success = await duty_repo.update_activity(
            confirmed_duty.id,
            title="Тестовая активность",
            description="Описание тестовой активности",
            activity_datetime=activity_time,
        )
        assert success, "Обновление активности должно быть успешным"
        print("   ✓ Активность обновлена успешно")

        # Test 3: Verify activity was saved
        print("✅ Тест 3: Проверка сохранения активности")
        updated_duty = await duty_repo.get_current_confirmed_duty(-1, -1)
        assert updated_duty is not None, "Дежурный все еще должен существовать"
        assert updated_duty.activity_title == "Тестовая активность", "Название должно совпадать"
        assert (
            updated_duty.activity_description == "Описание тестовой активности"
        ), "Описание должно совпадать"
        assert updated_duty.activity_datetime == activity_time, "Время должно совпадать"
        assert updated_duty.activity_set_at is not None, "Время установки должно быть проставлено"
        print("   ✓ Активность сохранена корректно")
        print(f"   - Название: {updated_duty.activity_title}")
        print(f"   - Описание: {updated_duty.activity_description}")
        print(f"   - Время: {updated_duty.activity_datetime}")
        print(f"   - Установлено: {updated_duty.activity_set_at}")

        print("🧹 Тестовые данные оставляем для проверки")


async def test_date_parsing():
    """Test date parsing functionality."""
    print("\n🧪 Тестирование парсинга дат")

    # Import parse_datetime from activity handler
    import sys
    import os

    sys.path.append(os.path.dirname(__file__))

    # Read the parse_datetime function from activity.py
    from src.handlers.activity import parse_datetime

    test_cases = [
        ("15.01.2024", "19:00", "2024-01-15 19:00:00"),
        ("15.01", "19:00", f"{datetime.now().year}-01-15 19:00:00"),
        ("15-01-2024", "19-00", "2024-01-15 19:00:00"),
        ("15-01", "19-00", f"{datetime.now().year}-01-15 19:00:00"),
    ]

    for date_str, time_str, expected_format in test_cases:
        try:
            result = parse_datetime(date_str, time_str)
            expected = datetime.strptime(expected_format, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
            assert result == expected, f"Неверный результат для {date_str} {time_str}"
            print(f"   ✓ {date_str} {time_str} -> {result}")
        except Exception as e:
            print(f"   ❌ Ошибка при парсинге {date_str} {time_str}: {e}")


if __name__ == "__main__":
    asyncio.run(test_activity_functionality())
    asyncio.run(test_date_parsing())
    print("\n🎉 Все тесты завершены успешно!")
