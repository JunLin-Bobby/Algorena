"""Alembic migration helpers (single schema path for app, tests, and CLI)."""

from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parent.parent
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def file_database_url(db_path: Path) -> str:
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


def to_sync_database_url(database_url: str) -> str:
    if database_url.startswith("sqlite+aiosqlite:"):
        return database_url.replace("sqlite+aiosqlite:", "sqlite:", 1)
    return database_url


def get_alembic_config(database_url: str | None = None) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    if database_url is not None:
        cfg.set_main_option("sqlalchemy.url", to_sync_database_url(database_url))
    cfg.attributes["configure_logger"] = False
    return cfg


def upgrade_head(database_url: str | None = None) -> None:
    if database_url is None:
        from config import get_settings

        database_url = get_settings().database_url
    command.upgrade(get_alembic_config(database_url), "head")


def downgrade(revision: str, database_url: str | None = None) -> None:
    if database_url is None:
        from config import get_settings

        database_url = get_settings().database_url
    command.downgrade(get_alembic_config(database_url), revision)
