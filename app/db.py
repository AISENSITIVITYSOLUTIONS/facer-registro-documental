from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_parent_dir(database_uri: str) -> None:
    if not database_uri.startswith("sqlite"):
        return

    path_part = database_uri.replace("sqlite:///", "", 1)
    if not path_part or path_part == ":memory:":
        return

    sqlite_path = Path(path_part)
    if not sqlite_path.is_absolute():
        sqlite_path = Path.cwd() / sqlite_path

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)


def _engine_kwargs(database_uri: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "pool_pre_ping": True,
        "future": True,
    }
    if database_uri.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return kwargs


_ensure_sqlite_parent_dir(settings.sqlalchemy_database_uri)
engine = create_engine(
    settings.sqlalchemy_database_uri,
    **_engine_kwargs(settings.sqlalchemy_database_uri),
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
