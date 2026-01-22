"""Application configuration and settings."""

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
    WEEKLY_DUTY_DAY: int = 0  # 0=Monday, 6=Sunday
    WEEKLY_DUTY_HOUR: int = 10
    WEEKLY_DUTY_MINUTE: int = 0

    # History Configuration
    HISTORY_LIMIT: int = 10  # Number of duty records to show in history

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


settings = Settings()
