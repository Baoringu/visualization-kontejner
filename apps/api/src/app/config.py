from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://pallet_building:change-me@localhost:5432/kontejner"
    redis_url: str = "redis://localhost:6379/0"
    session_cookie_name: str = "pallet_building_session"
    csrf_cookie_name: str = "pallet_building_csrf"
    session_ttl_hours: int = 12
    web_origin: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
