"""Application configuration using pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8099, alias="PORT")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    
    # Rate Limiting
    rate_limit_anonymous: str = Field(default="30/minute", alias="RATE_LIMIT_ANONYMOUS")
    rate_limit_authenticated: str = Field(default="120/minute", alias="RATE_LIMIT_AUTHENTICATED")
    
    # Cache TTL (seconds)
    cache_ttl_nowcast: int = Field(default=120, alias="CACHE_TTL_NOWCAST")
    cache_ttl_weather: int = Field(default=900, alias="CACHE_TTL_WEATHER")
    cache_ttl_earthquake_latest: int = Field(default=60, alias="CACHE_TTL_EARTHQUAKE_LATEST")
    cache_ttl_earthquake_list: int = Field(default=300, alias="CACHE_TTL_EARTHQUAKE_LIST")
    
    # API Keys (comma-separated)
    api_keys: str = Field(default="", alias="API_KEYS")

    # Admin Auth
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="changeme", alias="ADMIN_PASSWORD")
    
    # BMKG Base URLs
    bmkg_nowcast_base_url: str = Field(
        default="https://www.bmkg.go.id/alerts/nowcast",
        alias="BMKG_NOWCAST_BASE_URL"
    )
    bmkg_weather_base_url: str = Field(
        default="https://api.bmkg.go.id/publik",
        alias="BMKG_WEATHER_BASE_URL"
    )
    bmkg_earthquake_base_url: str = Field(
        default="https://data.bmkg.go.id/DataMKG/TEWS",
        alias="BMKG_EARTHQUAKE_BASE_URL"
    )
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Alert system (bmkg-alert)
    db_path: str = Field(default="data/bmkg_alert.db", alias="DB_PATH")
    bmkg_api_url: str = Field(default="https://bmkg-restapi.vercel.app", alias="BMKG_API_URL")
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")

    # Notifications
    discord_webhook_url: str | None = Field(default=None, alias="DISCORD_WEBHOOK_URL")
    slack_webhook_url: str | None = Field(default=None, alias="SLACK_WEBHOOK_URL")
    generic_webhook_url: str | None = Field(default=None, alias="GENERIC_WEBHOOK_URL")

    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = Field(default=None, alias="TELEGRAM_CHAT_ID")
    
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str | None = Field(default=None, alias="SMTP_USER")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="noreply@bmkg-alert.com", alias="SMTP_FROM")
    
    @property
    def api_key_list(self) -> list[str]:
        """Return list of valid API keys."""
        if not self.api_keys:
            return []
        return [key.strip() for key in self.api_keys.split(",") if key.strip()]


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Return the global settings instance."""
    return settings
