import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application Settings and Configuration."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "Newswire Compliance & Intelligence Monitor"
    APP_ENV: str = "production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./data/news.db"
    )

    # Scheduler & Background Ingestion
    AUTO_POLL_ENABLED: bool = True
    POLLING_INTERVAL_MINUTES: int = 15
    DEFAULT_ARTICLES_PER_FEED: int = 25
    REQUEST_TIMEOUT_SECONDS: int = 15

    # External APIs (Optional)
    NEWSAPI_KEY: Optional[str] = None
    GNEWS_API_KEY: Optional[str] = None

    # HTTP Client User-Agent
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36 NewswireBot/2.0"
    )

    # NLP & Compliance Configuration
    DEFAULT_LANGUAGE: str = "en"
    COMPLIANCE_CRITICAL_WEIGHT: float = 35.0
    COMPLIANCE_HIGH_WEIGHT: float = 20.0
    COMPLIANCE_MEDIUM_WEIGHT: float = 10.0
    COMPLIANCE_LOW_WEIGHT: float = 5.0


settings = Settings()
