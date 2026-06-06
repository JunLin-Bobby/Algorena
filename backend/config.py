"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

JudgeMode = Literal["mock", "llm"]

# config.py 所在目錄（backend/），作為相對路徑的基準，不受執行時 cwd 影響
# 預設 SQLite 檔案放在 backend/ 下，方便開發時與程式碼同層管理
# SQLAlchemy async 連線字串；as_posix() 將 Windows 路徑轉為 / 分隔，避免反斜線造成 URL 解析錯誤
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "algorena.db"
DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{DEFAULT_DB_PATH.as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # ─── 資料庫 ──────────────────────────────────────────
    database_url: str = DEFAULT_DATABASE_URL

    # ─── AI 評審（LLMJudgeService via OpenAI-compatible API）────
    judge_mode: JudgeMode = Field(default="mock", validation_alias="JUDGE_MODE")
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str | None = None
    llm_timeout_seconds: float = 20.0
    llm_max_tokens: int = 1024

    # ─── 遊戲規則 ────────────────────────────────────────
    game_duration_seconds: int = 300
    max_players: int = 2
    violation_penalty: int = 5

    # ─── CORS ────────────────────────────────────────────
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
