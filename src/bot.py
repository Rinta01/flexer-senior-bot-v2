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
from src.database.repositories import PoolRepository
from src.handlers import (
    activity,
    duty_callbacks,
    force_pick,
    help,
    history,
    join,
    leave,
    pick,
    pool,
    start,
    week_selection,
)
from src.middlewares.logging import LoggingMiddleware
from src.utils.logger import setup_logging
from src.services.duty_selector import select_and_announce_duty

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
        self.dp.include_router(pool.router)
        self.dp.include_router(pick.router)  # New: random duty selection
        self.dp.include_router(force_pick.router)
        self.dp.include_router(activity.router)  # Activity management
        self.dp.include_router(history.router)  # History command
        self.dp.include_router(help.router)  # Help command
        self.dp.include_router(week_selection.router)  # Week selection callbacks
        self.dp.include_router(duty_callbacks.router)  # Duty confirmation callbacks

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
            async with db_manager.async_session() as session:
                pool_repo = PoolRepository(session)
                pools = await pool_repo.get_all_pools()

                if not pools:
                    logger.info("No pools found for weekly duty selection")
                    return

                logger.info(f"Processing {len(pools)} pools for weekly duty selection")

                successful_selections = 0
                skipped_selections = 0
                failed_selections = 0

                for pool in pools:
                    try:
                        logger.info(
                            f"Auto-selecting duty for pool {pool.id} "
                            f"(group {pool.group_id}, '{pool.group_title}')"
                        )

                        # Use shared duty selection logic
                        result = await select_and_announce_duty(
                            session=session,
                            bot=self.bot,
                            pool_id=pool.id,
                            group_id=pool.group_id,
                            is_automatic=True,
                        )

                        if result["success"]:
                            # Check if it was actually assigned or just skipped
                            if result["result"] and result["result"].get("error") == "all_pending":
                                skipped_selections += 1
                            elif result["result"] and result["result"].get("already_assigned"):
                                skipped_selections += 1
                            else:
                                successful_selections += 1
                        else:
                            failed_selections += 1

                    except Exception as e:
                        logger.error(
                            f"Error selecting duty for pool {pool.id} (group {pool.group_id}): {e}",
                            exc_info=True,
                        )
                        failed_selections += 1
                        continue

                logger.info(
                    f"Weekly duty job completed: {successful_selections} successful, "
                    f"{skipped_selections} skipped, {failed_selections} failed "
                    f"out of {len(pools)} pools"
                )

        except Exception as e:
            logger.error(f"Error in weekly_duty_job: {e}", exc_info=True)

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
        from aiogram.types import BotCommandScopeAllGroupChats, BotCommandScopeDefault

        commands = [
            BotCommand(command="start", description="Показать справку"),
            BotCommand(command="join", description="Присоединиться к пулу"),
            BotCommand(command="leave", description="Выйти из пула"),
            BotCommand(command="pool", description="Список участников пула"),
            BotCommand(command="pick", description="Выбрать дежурного случайно"),
            BotCommand(command="activity", description="Дежурный и активность недели"),
            BotCommand(command="force_pick", description="Выбрать дежурного вручную"),
            BotCommand(
                command="set_activity", description="Установить активность (только дежурный)"
            ),
            BotCommand(command="history", description="История дежурств"),
            BotCommand(command="help", description="Полная справка"),
        ]

        # Set commands for private chats
        await self.bot.set_my_commands(commands, scope=BotCommandScopeDefault())

        # Set commands for all group chats
        await self.bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())

        logger.info("Set default commands for private and group chats")

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
            # Setup scheduler (currently disabled for manual duty selection)
            # self.setup_scheduler()
            # if self.scheduler:
            #     self.scheduler.start()
            logger.info("Automatic duty selection is disabled - use /pick command instead")

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
