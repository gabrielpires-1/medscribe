from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEDSCRIBE_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "medscribe"
    app_version: str = "0.1.0"
    pyannote_api_key: str
    pyannote_base_url: str = "https://api.pyannote.ai"
    pyannote_poll_interval_seconds: float = 10
    pyannote_poll_timeout_seconds: float = 600
    transcription_output_dir: Path = Path("data/transcriptions")


@lru_cache
def get_settings() -> Settings:
    return Settings()
