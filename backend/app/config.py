"""Application configuration using pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ADMIN_PASSWORD = "changeme"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    timezone: str = Field(default="Asia/Jakarta", alias="TZ")

    # Optional Redis for the response cache; falls back to memory when unreachable
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")

    # How long BMKG responses are reused, in seconds
    cache_ttl_nowcast: int = Field(default=120, alias="CACHE_TTL_NOWCAST")
    cache_ttl_weather: int = Field(default=900, alias="CACHE_TTL_WEATHER")
    cache_ttl_earthquake: int = Field(default=120, alias="CACHE_TTL_EARTHQUAKE")
    cache_ttl_wilayah: int = Field(default=86400, alias="CACHE_TTL_WILAYAH")

    # Admin auth
    admin_password: str = Field(default=DEFAULT_ADMIN_PASSWORD, alias="ADMIN_PASSWORD")

    # Header a trusted reverse proxy sets to the visitor's address, e.g.
    # "CF-Connecting-IP" behind Cloudflare or "X-Real-IP" behind nginx.
    # Empty: use the address of the direct peer.
    client_ip_header: str = Field(default="", alias="CLIENT_IP_HEADER")

    # Browser origins allowed to call the API directly (comma-separated).
    # The bundled frontend proxies /api on its own origin and needs none.
    cors_origins: str = Field(default="", alias="CORS_ORIGINS")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Alert system
    db_path: str = Field(default="data/bmkg_alert.db", alias="DB_PATH")
    bmkg_api_url: str = Field(default="https://bmkg-api.dhanypedia.com", alias="BMKG_API_URL")
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
    # Empty: send as SMTP_USER
    smtp_from: str = Field(default="", alias="SMTP_FROM")

    @property
    def admin_password_set(self) -> bool:
        """True once the owner replaced the well-known default password."""
        return bool(self.admin_password) and self.admin_password != DEFAULT_ADMIN_PASSWORD

    @property
    def write_locked(self) -> bool:
        """Whether changing settings needs the admin password.

        A public demo is always locked. A private instance is locked as soon as
        an admin password is configured; with the default password it stays
        open, as it has no secret to check against.
        """
        return self.demo_mode or self.admin_password_set

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Return the global settings instance."""
    return settings
