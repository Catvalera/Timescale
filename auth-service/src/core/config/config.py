from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):

    # --- tokens ---
    ACCESS_HEADER_TOKEN_NAME: str = "X-Access-Token"
    REFRESH_HEADER_TOKEN_NAME: str = "X-Refresh-Token"
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 1800
    REFRESH_TOKEN_EXPIRE_SECONDS: int = 604800
    VERIFY_TOKEN_EXPIRE_SECONDS: int = 600
    ALGORITHM_ENCRYPTION: str = "HS256"
    SECRET_KEY: str = "dev-secret-key-change-me-please-at-least-32-bytes"
    TOKEN_ISSUER: str = "auth-service"

    # --- verification codes ---
    CODE_EXPIRE_SECONDS: int = 600
    CODE_RESEND_SECONDS: int = 60
    CODE_MAX_ATTEMPTS: int = 5

    # --- database ---
    DB_NAME: str = "timescale_db"
    DB_SCHEMA: str = "auth"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_ECHO: bool = False

    # --- url ---
    MAIL_SERVICE: str = "http://localhost:8002/api/"
    MAIL_TIMEOUT_SECONDS: float = 20

    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
