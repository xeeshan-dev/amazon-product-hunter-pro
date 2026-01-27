"""
Production-grade configuration management
Loads settings from environment variables with validation
"""
import os
from typing import List, Optional
from pydantic import BaseSettings, validator, AnyHttpUrl
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with validation"""
    
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
    
    # Security
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 20
    RATE_LIMIT_PER_HOUR: int = 500
    
    # Database
    DATABASE_URL: str = "sqlite:///./amazon_hunter.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Scraping
    SCRAPING_ENABLED: bool = True
    MAX_CONCURRENT_REQUESTS: int = 5
    REQUEST_TIMEOUT: int = 30
    MIN_DELAY_SECONDS: float = 2.0
    MAX_DELAY_SECONDS: float = 5.0
    MAX_RETRIES: int = 3
    
    # Proxy
    USE_PROXY: bool = False
    PROXY_URL: Optional[str] = None
    PROXY_USERNAME: Optional[str] = None
    PROXY_PASSWORD: Optional[str] = None
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # External Services
    CAPTCHA_SOLVER_API_KEY: Optional[str] = None
    BRIGHT_DATA_PROXY_URL: Optional[str] = None
    
    # Amazon
    AMAZON_BASE_URL: str = "https://www.amazon.com"
    USER_AGENT_ROTATION: bool = True
    
    # Cache
    CACHE_TTL_SECONDS: int = 3600
    CACHE_ENABLED: bool = True
    
    # Background Jobs
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    @validator("SECRET_KEY", "JWT_SECRET_KEY")
    def validate_secrets(cls, v, field, values):
        # Skip validation in development/testing
        env = values.get('ENVIRONMENT', 'development')
        if env in ['development', 'testing']:
            return v or "dev-secret-key-minimum-32-chars-long"
        
        # Strict validation in production
        if not v or v == "your-secret-key-here-change-in-production":
            raise ValueError(f"{field.name} must be set in production")
        if len(v) < 32:
            raise ValueError(f"{field.name} must be at least 32 characters")
        return v
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Legacy Config class for backward compatibility
class Config:
    """Legacy configuration - kept for backward compatibility"""
    
    @staticmethod
    def _get_settings():
        return get_settings()
    
    @property
    def BASE_URL(self):
        return self._get_settings().AMAZON_BASE_URL
    
    @property
    def MIN_DELAY(self):
        return self._get_settings().MIN_DELAY_SECONDS
    
    @property
    def MAX_DELAY(self):
        return self._get_settings().MAX_DELAY_SECONDS
    
    @property
    def MAX_PAGES(self):
        return 5
    
    @property
    def BSR_WEIGHT(self):
        return 0.4
    
    @property
    def REVIEWS_WEIGHT(self):
        return 0.3
    
    @property
    def MARGIN_WEIGHT(self):
        return 0.3
    
    @property
    def BASE_FBA_FEE(self):
        return 5.0
    
    @property
    def FBA_PERCENTAGE(self):
        return 0.15
    
    @property
    def REFERRAL_FEE_PERCENTAGE(self):
        return 0.15
    
    @property
    def REQUESTS_PER_MINUTE(self):
        return self._get_settings().RATE_LIMIT_PER_MINUTE


# Create singleton instance
config = Config()
