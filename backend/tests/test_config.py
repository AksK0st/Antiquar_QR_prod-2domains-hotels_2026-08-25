import pytest
from pydantic import ValidationError

from config import Settings


BASE = {
    "postgres_db": "db",
    "postgres_user": "user",
    "postgres_password": "a-very-long-database-password",
    "postgres_host": "db",
    "minio_endpoint": "minio:9000",
    "minio_access_key": "application-user",
    "minio_secret_key": "a-very-long-storage-password",
    "minio_bucket": "images",
}


def test_production_rejects_http_and_localhost() -> None:
    with pytest.raises(ValidationError):
        Settings(**BASE, app_env="production", public_base_url="http://example.com")

    with pytest.raises(ValidationError):
        Settings(**BASE, app_env="production", public_base_url="https://localhost")


def test_production_rejects_example_secret() -> None:
    broken = dict(BASE)
    broken["postgres_password"] = "change_me"
    with pytest.raises(ValidationError):
        Settings(**broken, app_env="production", public_base_url="https://example.com")


def test_valid_production_settings_are_normalized() -> None:
    settings = Settings(
        **BASE,
        app_env="production",
        public_base_url="https://example.com/",
    )
    assert settings.public_base_url == "https://example.com"
    assert settings.public_origin == "https://example.com"
    assert settings.admin_session_cookie_name == "__Host-admin_session"
