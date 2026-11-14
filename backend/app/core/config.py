"""全局配置。所有环境变量集中在此，业务代码通过 settings 访问。"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    APP_NAME: str = "LightAgent"
    ENV: str = "dev"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "dev-only-secret-key-change-me-please-32b"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DATABASE_URL: str = f"sqlite+aiosqlite:///{(BASE_DIR / 'data' / 'lightagent.db').as_posix()}"
    REDIS_URL: str = ""

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    STORAGE_DIR: str = str(BASE_DIR / "storage")
    MAX_UPLOAD_MB: int = 50

    LLM_TIMEOUT_SECONDS: int = 120
    LLM_MAX_RETRIES: int = 2

    SSRF_ALLOW_PRIVATE: bool = False

    @property
    def cors_origins(self) -> List[str]:
        return [i.strip() for i in (self.CORS_ORIGINS or "").split(",") if i.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def storage_path(self) -> Path:
        p = Path(self.STORAGE_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # sqlite 场景确保目录存在
    if settings.is_sqlite:
        db_path = settings.DATABASE_URL.split("///")[-1]
        if db_path and db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    return settings


settings = get_settings()
