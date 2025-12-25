from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Arbitraggio Automatizzato"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/arbitraggio"
    DATABASE_ECHO: bool = False
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # eBay API (vecchia)
    EBAY_APP_ID: Optional[str] = None
    EBAY_CERT_ID: Optional[str] = None
    EBAY_DEV_ID: Optional[str] = None
    EBAY_REDIRECT_URI: Optional[str] = None
    EBAY_REFRESH_TOKEN: Optional[str] = None
    EBAY_SANDBOX: bool = True  # True per testing
    
    # eBay Browse API (nuova - per ricerca prezzi)
    EBAY_CLIENT_ID: Optional[str] = None  # Application ID (Client ID)
    EBAY_CLIENT_SECRET: Optional[str] = None  # Cert ID (Client Secret)
    
    # Etsy API
    ETSY_API_KEY: Optional[str] = None
    ETSY_SHARED_SECRET: Optional[str] = None
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    
    # Proxy per scraping
    PROXY_URL: Optional[str] = None
    
    # ScraperAPI
    SCRAPER_API_KEY: Optional[str] = None
    
    # AI Models
    REAL_ESRGAN_MODEL_PATH: str = "./ai_models/real_esrgan"
    LLAVA_MODEL_PATH: str = "./ai_models/llava"
    
    # Scraping settings
    SCRAPING_DELAY_MIN: float = 2.0
    SCRAPING_DELAY_MAX: float = 5.0
    SCRAPING_MAX_PAGES: int = 10
    
    # AI Validation thresholds
    AI_MIN_SCORE_AUTO_REJECT: int = 4
    AI_MIN_SCORE_APPROVE: int = 7
    AI_MIN_MARGIN_PERCENT: float = 25.0
    
    # Notifications
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
