from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


def test_settings_defaults() -> None:
    settings = Settings(pyannote_api_key="fake-api-key")
    assert settings.app_name == "medscribe"
    assert settings.app_version == "0.1.0"
    assert settings.pyannote_base_url == "https://api.pyannote.ai"
    assert settings.pyannote_poll_interval_seconds == 10
    assert settings.pyannote_poll_timeout_seconds == 600
    assert settings.transcription_output_dir == Path("data/transcriptions")


def test_pyannote_api_key_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MEDSCRIBE_PYANNOTE_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_get_settings_returns_cached_instance() -> None:
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()
    assert first is second
    get_settings.cache_clear()
