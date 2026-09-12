from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = f"sqlite:///{(ROOT / 'runtime' / 'game.db').as_posix()}"
    provider: Literal["mock", "deepseek", "openai"] = "mock"
    deepseek_api_key: str = ""
    openai_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    openai_model: str = "gpt-4.1-mini"
    model_timeout_seconds: float = 18
    model_daily_call_limit: int = 100
    cookie_secure: bool = False
    allowed_origins: str = "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:8765,http://localhost:8765"
    delivery_delay: float = 0.16

    def validate_deployment(self):
        if self.app_env == "production":
            if not self.database_url.startswith("postgresql"):
                raise ValueError("Production requires PostgreSQL")
            if not self.cookie_secure:
                raise ValueError("Production requires COOKIE_SECURE=true and HTTPS")


settings = Settings()
