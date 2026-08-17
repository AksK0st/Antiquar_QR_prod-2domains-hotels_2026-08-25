from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


_INSECURE_SECRET_VALUES = {
    "",
    "change_me",
    "changeme",
    "password",
    "secret",
    "admin",
    "minioadmin",
}

_INSECURE_SECRET_PREFIXES = (
    "replace_with_",
    "replace-me",
    "replace_me",
    "example_",
    "example-",
)

_RESERVED_PRODUCTION_HOSTS = {"example.com", "example.net", "example.org"}
_RESERVED_PRODUCTION_SUFFIXES = (".example", ".invalid", ".test", ".localhost")


class Settings(BaseSettings):
    # Application
    app_env: Literal["development", "production", "test"] = "development"
    sql_echo: bool = False
    log_level: str = "INFO"

    # Admin
    admin_session_ttl_hours: int = Field(default=12, ge=1, le=168)
    admin_image_max_bytes: int = Field(default=15 * 1024 * 1024, ge=1024)
    admin_image_max_pixels: int = Field(default=40_000_000, ge=1_000_000)
    admin_login_rate_limit_attempts: int = Field(default=5, ge=1, le=100)
    admin_login_rate_limit_window_seconds: int = Field(default=60, ge=10, le=3600)
    admin_login_block_seconds: int = Field(default=300, ge=10, le=86_400)

    # PostgreSQL
    postgres_db: str
    postgres_user: str
    postgres_password: SecretStr
    postgres_host: str = "db"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_pool_size: int = Field(default=5, ge=1, le=50)
    postgres_max_overflow: int = Field(default=5, ge=0, le=100)
    postgres_pool_timeout_seconds: int = Field(default=10, ge=1, le=120)
    postgres_statement_timeout_ms: int = Field(default=10_000, ge=100, le=300_000)

    # MinIO/S3
    minio_endpoint: str
    minio_access_key: SecretStr
    minio_secret_key: SecretStr
    minio_bucket: str
    minio_secure: bool = False
    minio_connect_timeout_seconds: float = Field(default=3.0, gt=0, le=60)
    minio_read_timeout_seconds: float = Field(default=15.0, gt=0, le=300)

    # Public app
    public_base_url: str = Field(default="http://localhost:5173", repr=False)
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_runtime_configuration(self) -> "Settings":
        parsed = urlparse(self.public_base_url)

        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("PUBLIC_BASE_URL must be an absolute http(s) URL")

        if self.is_production:
            if parsed.scheme != "https":
                raise ValueError("PUBLIC_BASE_URL must use https in production")

            hostname = (parsed.hostname or "").lower().rstrip(".")
            if hostname in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("PUBLIC_BASE_URL must not point to localhost in production")
            if hostname in _RESERVED_PRODUCTION_HOSTS or hostname.endswith(_RESERVED_PRODUCTION_SUFFIXES):
                raise ValueError("PUBLIC_BASE_URL must use a real production hostname")
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError("PUBLIC_BASE_URL must be a clean application URL without credentials/query/fragment")

            required_secrets = {
                "POSTGRES_PASSWORD": self.postgres_password.get_secret_value(),
                "MINIO_ACCESS_KEY": self.minio_access_key.get_secret_value(),
                "MINIO_SECRET_KEY": self.minio_secret_key.get_secret_value(),
            }

            for name, value in required_secrets.items():
                normalized = value.strip().lower()
                if normalized in _INSECURE_SECRET_VALUES or normalized.startswith(_INSECURE_SECRET_PREFIXES):
                    raise ValueError(f"{name} must be changed for production")

            if len(self.postgres_password.get_secret_value()) < 16:
                raise ValueError("POSTGRES_PASSWORD must be at least 16 characters in production")

            if len(self.minio_secret_key.get_secret_value()) < 16:
                raise ValueError("MINIO_SECRET_KEY must be at least 16 characters in production")

        self.public_base_url = self.public_base_url.rstrip("/")
        return self

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def admin_session_cookie_name(self) -> str:
        return "__Host-admin_session" if self.is_production else "admin_session"

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def public_origin(self) -> str:
        parsed = urlparse(self.public_base_url)
        default_port = (parsed.scheme == "https" and parsed.port == 443) or (
            parsed.scheme == "http" and parsed.port == 80
        )
        netloc = parsed.hostname or ""
        if parsed.port and not default_port:
            netloc = f"{netloc}:{parsed.port}"
        return f"{parsed.scheme}://{netloc}"


@lru_cache
def get_settings() -> Settings:
    secrets_dir = "/run/secrets" if Path("/run/secrets").is_dir() else None
    return Settings(_secrets_dir=secrets_dir)


settings = get_settings()
