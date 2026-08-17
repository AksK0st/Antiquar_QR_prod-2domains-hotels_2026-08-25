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
        Settings(**broken, app_env="production", public_base_url="https://museum.example-museum.ru")


def test_valid_production_settings_are_normalized() -> None:
    settings = Settings(
        **BASE,
        app_env="production",
        public_base_url="https://museum.example-museum.ru/",
    )
    assert settings.public_base_url == "https://museum.example-museum.ru"
    assert settings.public_origin == "https://museum.example-museum.ru"
    assert settings.admin_session_cookie_name == "__Host-admin_session"


def test_production_rejects_example_placeholders() -> None:
    broken = dict(BASE)
    broken["postgres_password"] = "REPLACE_WITH_A_LONG_RANDOM_DATABASE_PASSWORD"
    broken["minio_secret_key"] = "REPLACE_WITH_A_LONG_RANDOM_APP_PASSWORD"
    with pytest.raises(ValidationError):
        Settings(
            **broken,
            app_env="production",
            public_base_url="https://museum.example-museum.ru",
        )


def test_production_accepts_real_host_and_non_placeholder_secrets() -> None:
    values = dict(BASE)
    values["postgres_password"] = "db-2N64DbF0sKtxh1uQ3"
    values["minio_secret_key"] = "s3-VkK7pM9gQ2rT6xL4z"
    settings = Settings(
        **values,
        app_env="production",
        public_base_url="https://museum.example-museum.ru",
    )
    assert settings.public_origin == "https://museum.example-museum.ru"


def test_production_rejects_base_path_and_invalid_bucket() -> None:
    with pytest.raises(ValidationError):
        Settings(
            **BASE,
            app_env="production",
            public_base_url="https://museum.example-museum.ru/catalog",
        )

    broken = dict(BASE)
    broken["minio_bucket"] = "bad..bucket"
    with pytest.raises(ValidationError):
        Settings(
            **broken,
            app_env="production",
            public_base_url="https://museum.example-museum.ru",
        )


def test_minio_bucket_rejects_uppercase_and_ip_like_name() -> None:
    broken = dict(BASE)
    broken["minio_bucket"] = "Bad-Bucket"
    with pytest.raises(ValidationError):
        Settings(**broken)

    broken["minio_bucket"] = "192.168.1.1"
    with pytest.raises(ValidationError):
        Settings(
            **broken,
            app_env="production",
            public_base_url="https://museum.example-museum.ru",
        )
