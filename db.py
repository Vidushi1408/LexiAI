# db.py
"""
SQLAlchemy engine, session factory and ORM models for Lexi AI's persistent state:
users, the audit log, and per-browser-session knowledge-base state.

Runs against Postgres in production (docker-compose and CI both provide one) or a local SQLite
file for zero-setup development — see config.settings.database_url. The schema is simple enough
to stay portable between the two; there is no migration framework yet (Alembic would be the next
step once the schema needs to change under real data — noted here rather than silently skipped).
"""
import datetime as dt
import logging
import os

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, LargeBinary, String, Text, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings

log = logging.getLogger("lexi.db")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    username = Column(String(32), primary_key=True)
    role = Column(String(16), nullable=False)
    password_hash = Column(String(255), nullable=False)
    api_key_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class AuditEntry(Base):
    __tablename__ = "audit_log"
    seq = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(String(40), nullable=False)
    user = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    details = Column(JSON, nullable=False, default=dict)
    prev_hash = Column(String(64), nullable=False)
    hash = Column(String(64), nullable=False)


class KBSessionRow(Base):
    """One row per browser session's knowledge base — see webapp/state.py.
    Rows for zero-retention sessions are never written here (see that module)."""
    __tablename__ = "kb_sessions"
    sid = Column(String(32), primary_key=True)
    raw_text = Column(Text, nullable=True)
    file_name = Column(String(1024), nullable=True)
    pages = Column(JSON, nullable=True)
    processed = Column(Boolean, default=False)
    faiss_index = Column(LargeBinary, nullable=True)
    chunks = Column(JSON, nullable=True)
    pipeline_result = Column(JSON, nullable=True)
    summary_result = Column(Text, nullable=True)
    compliance_result = Column(JSON, nullable=True)
    entities_result = Column(JSON, nullable=True)
    action_items_result = Column(JSON, nullable=True)
    # Past runs, newest last, capped at HISTORY_LIMIT (see webapp/state.py) — the fields above
    # stay as "the latest run" so nothing that reads them needs to change.
    briefing_history = Column(JSON, nullable=True)
    compliance_history = Column(JSON, nullable=True)
    entities_history = Column(JSON, nullable=True)
    action_items_history = Column(JSON, nullable=True)
    zero_retention = Column(Boolean, default=False)
    last_audited_question = Column(Text, nullable=True)
    qa_confidences = Column(JSON, nullable=True)
    flat_ingestion = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)


_engine = None
_SessionLocal = None


def _make_engine(url: str):
    if url.startswith("sqlite"):
        os.makedirs(os.path.dirname(url.removeprefix("sqlite:///")) or ".", exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


def get_engine():
    global _engine
    if _engine is None:
        _engine = _make_engine(settings.database_url)
    return _engine


def get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def new_session():
    """A fresh SQLAlchemy session. Callers are responsible for closing it (use as a context manager)."""
    return get_sessionmaker()()


def init_db() -> None:
    """Create tables that don't exist yet, then patch any table that's missing columns a model
    has gained since it was first created (see the module docstring re: no migration framework).
    Safe to call on every app startup."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    _add_missing_columns(engine)


def _add_missing_columns(engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    try:
        with engine.begin() as conn:
            for table in Base.metadata.sorted_tables:
                if table.name not in existing_tables:
                    continue  # create_all() above just made it, with every column already
                existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
                for col in table.columns:
                    if col.name in existing_cols:
                        continue
                    col_type = col.type.compile(dialect=engine.dialect)
                    conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col_type}'))
                    log.warning("schema upgrade: added column %s.%s", table.name, col.name)
    except Exception:
        log.exception("schema upgrade failed; continuing with the existing schema")


def reset_engine_for_tests(url: str | None = None) -> None:
    """
    Point db.py at a fresh, empty schema — for test fixtures only. Defaults to DATABASE_URL when
    set (CI provides a real Postgres service, so the suite runs against the same database engine
    as production) and otherwise to an isolated local SQLite file, so plain `pytest` locally needs
    no services running. Drops tables first: DATABASE_URL, unlike a fresh SQLite file, points at a
    long-lived server shared by the whole test run, so each test still needs to start empty.
    """
    global _engine, _SessionLocal
    url = url or os.getenv("DATABASE_URL") or "sqlite:///:memory:"
    if _engine is not None:
        _engine.dispose()
    _engine = _make_engine(url)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    Base.metadata.drop_all(_engine)
    Base.metadata.create_all(_engine)
