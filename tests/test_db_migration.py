# tests/test_db_migration.py
"""init_db() must upgrade an existing table in place when a model gains a new column, without
touching the rows already there — a safety net for anyone who starts the app without running
`alembic upgrade head` by hand (see db.py). It must also leave the database stamped at Alembic's
head revision, so a later real `alembic upgrade head` doesn't try to replay "create table" against
tables that already exist."""
from pathlib import Path

import sqlalchemy as sa

import db


def test_init_db_adds_missing_column_to_existing_table_and_keeps_its_rows(tmp_path):
    url = f"sqlite:///{tmp_path}/legacy.db"
    engine = sa.create_engine(url)

    # Simulate a database created before `briefing_history` existed on KBSessionRow.
    old_columns = [c for c in db.KBSessionRow.__table__.columns if c.name != "briefing_history"]
    legacy_table = sa.Table("kb_sessions", sa.MetaData(), *(c.copy() for c in old_columns))
    legacy_table.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(legacy_table.insert().values(sid="abc123", file_name="contract.pdf"))
    engine.dispose()

    prior_engine, prior_sessionmaker = db._engine, db._SessionLocal
    db._engine = db._make_engine(url)
    db._SessionLocal = None
    try:
        db.init_db()
        inspector = sa.inspect(db.get_engine())
        columns = {c["name"] for c in inspector.get_columns("kb_sessions")}
        assert "briefing_history" in columns

        with db.get_engine().begin() as conn:
            row = conn.execute(sa.text("SELECT sid, file_name, briefing_history FROM kb_sessions")).fetchone()
        assert row.sid == "abc123"
        assert row.file_name == "contract.pdf"
        assert row.briefing_history is None

        with db.get_engine().begin() as conn:
            stamped = conn.execute(sa.text("SELECT version_num FROM alembic_version")).fetchone()
        assert stamped is not None
    finally:
        db._engine, db._SessionLocal = prior_engine, prior_sessionmaker


def test_init_db_stamps_a_fresh_database_at_head(tmp_path):
    url = f"sqlite:///{tmp_path}/fresh.db"
    prior_engine, prior_sessionmaker = db._engine, db._SessionLocal
    db._engine = db._make_engine(url)
    db._SessionLocal = None
    try:
        db.init_db()
        with db.get_engine().begin() as conn:
            stamped = conn.execute(sa.text("SELECT version_num FROM alembic_version")).fetchone()
        assert stamped is not None

        # A real `alembic upgrade head` afterwards must be a no-op, not an error, since the
        # tables it thinks it needs to create already exist.
        from alembic import command
        from alembic.config import Config

        cfg = Config(str(Path(db.__file__).resolve().parent / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", url)
        command.upgrade(cfg, "head")
    finally:
        db._engine, db._SessionLocal = prior_engine, prior_sessionmaker


def test_init_db_restamps_a_database_left_at_an_older_revision(tmp_path):
    """Regression: an earlier version of _ensure_alembic_stamped only stamped a database that had
    no alembic_version table at all, so one stamped before a later migration was added (e.g. by an
    older deploy of this app) stayed pinned to that old revision forever — even though create_all()
    and the column-patcher had already brought its columns up to date. init_db() must catch it up
    to head every time, not just the first time."""
    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    url = f"sqlite:///{tmp_path}/stale.db"
    cfg = Config(str(Path(db.__file__).resolve().parent / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    script = ScriptDirectory.from_config(cfg)
    head = script.get_current_head()
    previous = script.get_revision(head).down_revision
    assert previous is not None, "this regression test needs at least two migrations to exist"

    prior_engine, prior_sessionmaker = db._engine, db._SessionLocal
    db._engine = db._make_engine(url)
    db._SessionLocal = None
    try:
        db.init_db()
        command.stamp(cfg, previous)   # simulate a database stamped before the latest migration existed

        db.init_db()
        with db.get_engine().begin() as conn:
            stamped = conn.execute(sa.text("SELECT version_num FROM alembic_version")).fetchone()[0]
        assert stamped == head
    finally:
        db._engine, db._SessionLocal = prior_engine, prior_sessionmaker
