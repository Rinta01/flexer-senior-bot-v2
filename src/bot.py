"""Main bot application entry point."""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import (  # pyright: ignore[reportMissingTypeStubs]
    AsyncIOScheduler,
)

from src.config import settings
from src.database.engine import db_manager
from src.handlers import duty, join, leave, start
from src.middlewares.logging import LoggingMiddleware
from src.utils.logger import setup_logging

logger = setup_logging(__name__)


class FlexerBot:
    """Main bot application class."""

    def __init__(self):
        """Initialize bot application."""
        self.bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.dp = Dispatcher()
        self.scheduler: AsyncIOScheduler | None = None
        self.setup_handlers()
        self.setup_middleware()

    def setup_handlers(self) -> None:
        """Register command handlers."""
        logger.info("Setting up handlers...")

        # Register routers
        self.dp.include_router(start.router)
        self.dp.include_router(join.router)
        self.dp.include_router(leave.router)
        self.dp.include_router(duty.router)

    def setup_middleware(self) -> None:
        """Setup middlewares."""
        logger.info("Setting up middlewares...")
        self.dp.message.middleware(LoggingMiddleware())

    def setup_scheduler(self) -> None:
        """Setup APScheduler for weekly duty selection."""
        logger.info("Setting up scheduler...")

        self.scheduler = AsyncIOScheduler()

        # Add job for weekly duty announcement
        self.scheduler.add_job(  # pyright: ignore[reportUnknownMemberType]
            self.weekly_duty_job,
            trigger="cron",
            day_of_week=settings.WEEKLY_DUTY_DAY,
            hour=settings.WEEKLY_DUTY_HOUR,
            minute=settings.WEEKLY_DUTY_MINUTE,
            id="weekly_duty_selection",
        )

        logger.info(
            f"Scheduled weekly duty selection for "
            f"{self.get_weekday_name(settings.WEEKLY_DUTY_DAY)} "
            f"{settings.WEEKLY_DUTY_HOUR:02d}:{settings.WEEKLY_DUTY_MINUTE:02d}"
        )

    async def weekly_duty_job(self) -> None:
        """Job to select and announce weekly duty."""
        logger.info("Running weekly duty selection job...")

        try:
            # This would need to iterate through all active pools
            # For now, placeholder for future enhancement
            logger.info("Weekly duty job completed")

        except Exception as e:
            logger.error(f"Error in weekly_duty_job: {e}")

    @staticmethod
    def get_weekday_name(day: int) -> str:
        """Get weekday name from ISO weekday number."""
        days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        return days[day % 7]

    async def set_default_commands(self) -> None:
        """Set bot default commands."""
        commands = [
            BotCommand(command="start", description="Показать справку"),
            BotCommand(command="join", description="Присоединиться к пулу"),
            BotCommand(command="leave", description="Выйти из пула"),
            BotCommand(command="duty", description="Текущий дежурный"),
            BotCommand(command="help", description="Полная справка"),
        ]

        await self.bot.set_my_commands(commands)
        logger.info("Set default commands")

    async def startup(self) -> None:
        """Bot startup routine."""
        logger.info("Starting bot...")

        try:
            # Create tables if not exist
            await db_manager.create_tables()
            logger.info("Database tables created/verified")

            # Set default commands
            await self.set_default_commands()

            # Get bot info
            bot_info = await self.bot.get_me()
            logger.info(f"Bot started: @{bot_info.username}")

        except Exception as e:
            logger.error(f"Error during startup: {e}")
            raise

    async def shutdown(self) -> None:
        """Bot shutdown routine."""
        logger.info("Shutting down bot...")

        try:
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown()

            await db_manager.close()
            await self.bot.session.close()
            logger.info("Bot shut down successfully")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def start_polling(self) -> None:
        """Start bot in polling mode."""
        logger.info("Starting long polling...")

        await self.startup()

        try:
            # Setup scheduler
            self.setup_scheduler()
            if self.scheduler:
                self.scheduler.start()

            # Start polling
            await self.dp.start_polling(self.bot)  # pyright: ignore[reportUnknownMemberType]

        except Exception as e:
            logger.error(f"Error during polling: {e}")
            raise

        finally:
            await self.shutdown()


async def main() -> None:
    """Main entry point."""
    bot = FlexerBot()
    await bot.start_polling()


if __name__ == "__main__":
    asyncio.run(main())
