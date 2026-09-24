# tests/test_db_migration.py
"""init_db() must upgrade an existing table in place when a model gains a new column, without
touching the rows already there — this is the only safety net until Alembic lands (see db.py)."""
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
    finally:
        db._engine, db._SessionLocal = prior_engine, prior_sessionmaker
