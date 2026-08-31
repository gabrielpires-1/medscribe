from app.config import Settings, get_settings


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.app_name == "medscribe"
    assert settings.app_version == "0.1.0"


def test_get_settings_returns_cached_instance() -> None:
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()
    assert first is second
    get_settings.cache_clear()
