"""
Database engine, session factory and declarative base.

Uses SQLAlchemy 2.0.  Defaults to a local SQLite file (zero configuration)
but works unchanged with PostgreSQL or MySQL by editing ``DATABASE_URL`` in
``.env``.
"""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import PROJECT_ROOT, settings


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""


def _normalize_sqlite_url(url: str) -> str:
    """Anchor a *relative* SQLite file path to the project root.

    ``sqlite:///./nailstudio.db`` normally resolves against the current working
    directory, which would move the database file depending on where the server
    was launched from. Rewriting it to an absolute path under the project root
    keeps the database in one predictable place. Absolute paths
    (``sqlite:////var/data/db``), the in-memory database (``sqlite://``) and
    non-SQLite URLs are left untouched.
    """
    prefix = "sqlite:///"
    if url.startswith(prefix) and not url.startswith("sqlite:////"):
        raw = url[len(prefix):]
        if raw and ":memory:" not in raw:
            p = Path(raw)
            if not p.is_absolute():
                p = (PROJECT_ROOT / p).resolve()
                url = f"sqlite:///{p.as_posix()}"
    return url


def _make_engine(url: str):
    """Create an engine with sensible, database-specific options."""
    connect_args: dict = {}
    engine_kwargs: dict = {"pool_pre_ping": True, "future": True}

    if url.startswith("sqlite"):
        # SQLite needs this so the connection can be shared across FastAPI's
        # worker threads.
        connect_args["check_same_thread"] = False
        # An in-memory SQLite DB (used by the test-suite) must use a single
        # shared connection or every session would see an empty database.
        if ":memory:" in url or url.endswith("sqlite://"):
            engine_kwargs["poolclass"] = StaticPool

    return create_engine(url, connect_args=connect_args, **engine_kwargs)


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return _normalize_sqlite_url(url)


engine = _make_engine(normalize_database_url(settings.DATABASE_URL))

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Create all tables if they do not yet exist.

    For SQLite this is all that is required to get running.  For production
    PostgreSQL/MySQL, Alembic migrations (see /alembic) are the recommended
    path, but ``create_all`` remains safe and idempotent.
    """
    # Import models so they are registered on the metadata before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
