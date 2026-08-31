from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEDSCRIBE_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "medscribe"
    app_version: str = "0.1.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
