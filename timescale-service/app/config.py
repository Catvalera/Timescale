"""Настройки приложения (аналог appsettings.json)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Аналог ConnectionStrings:DefaultConnection
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/timescale_db"

    # Проверка токенов auth-service: имена переменных совпадают с .env сервиса авторизации
    secret_key: str = "dev-secret-key-change-me-please-at-least-32-bytes"   # SECRET_KEY
    algorithm_encryption: str = "HS256"                                      # ALGORITHM_ENCRYPTION
    access_header_token_name: str = "X-Access-Token"                         # ACCESS_HEADER_TOKEN_NAME
    token_issuer: str = "auth-service"                                       # TOKEN_ISSUER

    cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"


settings = Settings()
