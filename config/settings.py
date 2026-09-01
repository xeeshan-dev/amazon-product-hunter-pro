"""
Canonical application settings.

Environment values are loaded from the project-root `.env` file and process
environment variables. Keep legacy `Config` class attributes here until the
older scraper/scoring modules are refactored to dependency-injected settings.
"""
from functools import lru_cache
from typing import Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Amazon Hunter Pro"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    API_RELOAD: bool = False
    ALLOWED_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    # Security
    SECRET_KEY: str = "dev-secret-key-minimum-32-chars-long"
    JWT_SECRET_KEY: str = "dev-jwt-secret-key-minimum-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 20
    RATE_LIMIT_PER_HOUR: int = 500

    # Persistence
    DATABASE_URL: str = "sqlite:///./amazon_hunter.db"
    TRACKING_DATABASE_URL: str = "sqlite:///./web_app/backend/data/amazon_hunter.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Scraping
    SCRAPING_ENABLED: bool = True
    MAX_CONCURRENT_REQUESTS: int = 5
    REQUEST_TIMEOUT: int = 30
    MIN_DELAY_SECONDS: float = 3.0
    MAX_DELAY_SECONDS: float = 8.0
    MAX_RETRIES: int = 3
    AMAZON_BASE_URL: str = "https://www.amazon.com"
    USER_AGENT_ROTATION: bool = True

    # Enhanced Anti-Blocking
    USE_SMART_FETCHER: bool = True
    ENABLE_BROWSER_FALLBACK: bool = True
    BROWSER_HEADLESS: bool = True
    ENABLE_PROXY_ROTATION: bool = False
    ENABLE_CAPTCHA_HANDLING: bool = True
    ADAPTIVE_RATE_LIMITING: bool = True
    TLS_FINGERPRINTING: bool = True
    TWO_CAPTCHA_API_KEY: Optional[str] = None

    # Proxy
    USE_PROXY: bool = False
    PROXY_URL: Optional[str] = None
    PROXY_USERNAME: Optional[str] = None
    PROXY_PASSWORD: Optional[str] = None

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # External services
    CAPTCHA_SOLVER_API_KEY: Optional[str] = None
    BRIGHT_DATA_PROXY_URL: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    LLM_MODEL: str = "llama-3.3-70b-versatile"

    # Email
    EMAIL_PROVIDER: str = "smtp"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SENDGRID_API_KEY: str = ""
    EMAIL_FROM: str = ""
    EMAIL_FROM_NAME: str = "Amazon Hunter Pro"

    # Cache
    CACHE_TTL_SECONDS: int = 3600
    CACHE_ENABLED: bool = True

    # Product observation freshness
    OBSERVATION_FRESH_HOURS: int = 6
    OBSERVATION_STALE_HOURS: int = 48

    # Background jobs
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    @field_validator(
        "DEBUG",
        "API_RELOAD",
        "SCRAPING_ENABLED",
        "USER_AGENT_ROTATION",
        "USE_PROXY",
        "CACHE_ENABLED",
        mode="before",
    )
    @classmethod
    def parse_bool(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off", ""}:
                return False
            return False
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.ENVIRONMENT != "production":
            return self

        weak_values = {
            "",
            "your-secret-key-here-change-in-production",
            "your-jwt-secret-key-here",
            "dev-secret-key-minimum-32-chars-long",
            "dev-jwt-secret-key-minimum-32-chars",
        }
        for field_name in ("SECRET_KEY", "JWT_SECRET_KEY"):
            value = getattr(self, field_name)
            if value in weak_values or len(value) < 32:
                raise ValueError(f"{field_name} must be a strong production secret")
        return self

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == "testing"

    @property
    def allowed_origins(self) -> list[str]:
        configured = [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]
        # Local development commonly alternates between localhost and the
        # loopback IP. Keep both aliases available even if an older .env or
        # process-level ALLOWED_ORIGINS value contains only one of them.
        local_origins = {
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        }
        return list(dict.fromkeys(configured + sorted(local_origins)))


@lru_cache()
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()


_settings = get_settings()


class Config:
    """Legacy class-attribute config used by the scraper module.

    Scoring weights (BSR_WEIGHT, REVIEWS_WEIGHT, MARGIN_WEIGHT) have been
    removed — scoring is now owned exclusively by EnhancedOpportunityScorer
    in src/analysis/enhanced_scoring.py.
    FBA fee constants are kept for the scraper's _calculate_fba_fees fallback.
    """

    BASE_URL = _settings.AMAZON_BASE_URL
    MIN_DELAY = _settings.MIN_DELAY_SECONDS
    MAX_DELAY = _settings.MAX_DELAY_SECONDS
    MAX_PAGES = 5
    BASE_FBA_FEE = 5.0
    FBA_PERCENTAGE = 0.15
    REFERRAL_FEE_PERCENTAGE = 0.15
    REQUESTS_PER_MINUTE = _settings.RATE_LIMIT_PER_MINUTE


config = Config()
