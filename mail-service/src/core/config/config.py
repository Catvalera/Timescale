from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    TEMPLATES_PATH: Path = BASE_DIR / "templates"

    # --- email ---
    EMAIL_HOST: str = "localhost"
    EMAIL_PORT: int = 1025
    EMAIL_HOST_USER: str = "no-reply@example.com"
    EMAIL_PASSWORD: SecretStr = SecretStr("")
    EMAIL_FROM_NAME: str = "Timescale App"
    EMAIL_STARTTLS: bool = False
    EMAIL_SSL_TLS: bool = False
    EMAIL_USE_CREDENTIALS: bool = False
    EMAIL_TIMEOUT: int = 15

    # --- оформление писем ---
    APP_NAME: str = "Timescale App"
    LOGO_URL: str = ""
    APP_URL: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
