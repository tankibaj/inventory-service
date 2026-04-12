from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str  # Required — set via DATABASE_URL env var or .env file
    app_env: str = "development"
    log_level: str = "INFO"
    service_name: str = "inventory-service"
    service_version: str = "0.1.0"
    reservation_ttl_minutes: int = 15
    # When true, NullPool is used (no connection pooling) — for tests and CI
    database_use_null_pool: bool = False


def get_settings() -> Settings:
    return Settings()
