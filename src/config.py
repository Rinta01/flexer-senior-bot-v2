"""Application configuration and settings."""

from datetime import time

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Bot Configuration
    BOT_TOKEN: str = ""  # Will be loaded from .env file
    APP_NAME: str = "flexer-senior-bot"

    # Database Configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./flexer_senior.db"
    DATABASE_ECHO: bool = False

    # Application Configuration
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    # Scheduler Configuration
    WEEKLY_DUTY_ENABLED: bool = True
    WEEKLY_DUTY_DAY: int = 6  # 0=Monday, 6=Sunday
    WEEKLY_DUTY_TIME: str = "15:00"  # Always interpreted as UTC+3
    WEEKLY_DUTY_HOUR: int | None = None  # Legacy; prefer WEEKLY_DUTY_TIME
    WEEKLY_DUTY_MINUTE: int | None = None  # Legacy; prefer WEEKLY_DUTY_TIME

    # History Configuration
    HISTORY_LIMIT: int = 10  # Number of duty records to show in history

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    def get_weekly_duty_time(self) -> time:
        """Parse weekly duty time from HH:MM settings."""
        try:
            hour_text, minute_text = self.WEEKLY_DUTY_TIME.split(":", maxsplit=1)
            hour = int(hour_text)
            minute = int(minute_text)
            if not 0 <= hour <= 23 or not 0 <= minute <= 59:
                raise ValueError
            return time(hour=hour, minute=minute)
        except ValueError as exc:
            raise ValueError(
                "WEEKLY_DUTY_TIME must be in HH:MM format, for example 15:00"
            ) from exc

    def get_weekly_duty_day(self) -> int:
        """Return configured scheduler weekday."""
        if not 0 <= self.WEEKLY_DUTY_DAY <= 6:
            raise ValueError("WEEKLY_DUTY_DAY must be between 0 (Monday) and 6 (Sunday)")
        return self.WEEKLY_DUTY_DAY


settings = Settings()
