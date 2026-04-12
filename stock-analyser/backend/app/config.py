from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App info
    APP_NAME: str = "Indian Stock Analyser"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENABLE_SCHEDULER: bool = True
    CORS_ORIGINS: str = "*"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Market config (IST timezone)
    MARKET_OPEN_TIME: str = "09:15"
    MARKET_CLOSE_TIME: str = "15:30"
    PRE_MARKET_ANALYSIS_TIME: str = "08:30"   # Daily analysis cron time
    TIMEZONE: str = "Asia/Kolkata"

    # Stock selection
    MAX_RECOMMENDATIONS: int = 10
    MIN_SCORE_THRESHOLD: int = 45           # Minimum score to qualify
    MIN_MARKET_CAP_CR: float = 500.0        # Minimum market cap in Crores

    # Technical thresholds
    RSI_MIN: float = 40.0
    RSI_MAX: float = 68.0
    MIN_VOLUME_RATIO: float = 1.1           # Volume vs 20-day average
    MIN_ADX: float = 18.0                   # Minimum ADX for trend strength

    # Risk management
    MAX_STOP_LOSS_PCT: float = 2.0          # Max 2% stop loss
    MIN_STOP_LOSS_PCT: float = 0.4          # Minimum 0.4% stop loss
    TARGET1_RR_RATIO: float = 1.5           # Target 1: 1:1.5 Risk:Reward
    TARGET2_RR_RATIO: float = 2.5           # Target 2: 1:2.5 Risk:Reward

    # Data
    DATA_LOOKBACK_PERIOD: str = "6mo"       # Period for historical data
    DB_PATH: str = "stock_analyser.db"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def get_cors_origins() -> list[str]:
    if settings.CORS_ORIGINS.strip() == "*":
        return ["*"]

    return [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
