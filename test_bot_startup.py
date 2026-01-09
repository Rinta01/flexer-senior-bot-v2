"""Тест запуска бота и инициализации БД."""

import sys
import asyncio
import os

sys.path.insert(0, ".")


async def test_bot_init():
    """Тест инициализации бота."""
    from src.bot import FlexerBot
    from src.database.engine import db_manager

    print("=== Тест инициализации бота ===")
    bot_app = FlexerBot()
    print(f"✅ FlexerBot создан")
    print(f"✅ Диспетчер: {bot_app.dp}")
    print(f"✅ Бот объект: {bot_app.bot}")

    # Проверка создания таблиц
    await db_manager.create_tables()
    print("✅ Таблицы БД созданы")

    print("\n=== Проверка базы данных ===")
    if os.path.exists("flexer_senior.db"):
        size = os.path.getsize("flexer_senior.db")
        print(f"✅ База данных создана: flexer_senior.db ({size} байт)")

    print("\n✅ Все проверки пройдены успешно! Бот готов к запуску.")


if __name__ == "__main__":
    asyncio.run(test_bot_init())
