from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://inventory:inventory@localhost:5432/inventory"
    app_env: str = "development"
    log_level: str = "INFO"
    service_name: str = "inventory-service"
    service_version: str = "0.1.0"
    reservation_ttl_minutes: int = 15


def get_settings() -> Settings:
    return Settings()
