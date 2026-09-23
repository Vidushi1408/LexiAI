import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch

import numpy as np
import pytest

import db
from audit import log as audit
from rag import indexer


@pytest.fixture
def db_session():
    """An isolated in-memory SQLite session per test — same tables as production Postgres."""
    db.reset_engine_for_tests()  # DATABASE_URL (a real Postgres in CI) or an in-memory SQLite fallback
    s = db.new_session()
    yield s
    s.close()


def test_chain_verifies_and_records_metadata(db_session):
    audit.record("documents_uploaded", user="priya", session=db_session, documents=["a.pdf"])
    audit.record("question_asked", user="priya", session=db_session, query=audit.fingerprint("secret question"))
    assert audit.verify(db_session) == (True, "Audit log intact (2 entries).")
    rows = audit.read(db_session)
    assert "secret question" not in str(rows)
    assert rows[1]["prev_hash"] == rows[0]["hash"]


def test_tampering_is_detected(db_session):
    for i in range(3):
        audit.record("x", session=db_session, i=i)
    row = db_session.get(db.AuditEntry, 2)
    row.user = "someone_else"
    db_session.commit()
    ok, msg = audit.verify(db_session)
    assert not ok and "#2" in msg


def test_deleting_an_entry_is_detected(db_session):
    for i in range(3):
        audit.record("x", session=db_session, i=i)
    row = db_session.get(db.AuditEntry, 2)
    db_session.delete(row)
    db_session.commit()
    assert not audit.verify(db_session)[0]


def test_csv_export_has_all_rows(db_session):
    audit.record("a", session=db_session)
    audit.record("b", session=db_session)
    assert len(audit.export_csv(db_session).strip().splitlines()) == 3   # header + 2


def test_read_limit_returns_the_most_recent_entries(db_session):
    for i in range(5):
        audit.record("x", session=db_session, i=i)
    last_two = audit.read(db_session, limit=2)
    assert [e["details"]["i"] for e in last_two] == [3, 4]


def _fake_embed(chunks, use_cache=True):
    rng = np.random.default_rng(0)
    v = rng.random((len(chunks), 8)).astype(np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def test_zero_retention_writes_nothing_to_disk(tmp_path):
    idx_dir = tmp_path / "saved_index"
    with patch.object(indexer, "_INDEX_DIR", str(idx_dir)), \
         patch.object(indexer, "_INDEX_FILE", str(idx_dir / "faiss.index")), \
         patch.object(indexer, "_CHUNKS_FILE", str(idx_dir / "chunks.pkl")), \
         patch.object(indexer, "_HASH_FILE", str(idx_dir / "text_hash.txt")), \
         patch("embeddings.sentence_embeddings.embed_sentences", side_effect=_fake_embed) as emb:
        index, chunks = indexer.index_document("First clause. Second clause. Third clause. Fourth clause.",
                                               persist=False)
    assert index.ntotal == len(chunks) > 0
    assert not idx_dir.exists()                          # nothing saved
    assert emb.call_args.kwargs["use_cache"] is False    # embedding cache disabled too


def test_normal_mode_still_persists(tmp_path):
    idx_dir = tmp_path / "saved_index"
    with patch.object(indexer, "_INDEX_DIR", str(idx_dir)), \
         patch.object(indexer, "_INDEX_FILE", str(idx_dir / "faiss.index")), \
         patch.object(indexer, "_CHUNKS_FILE", str(idx_dir / "chunks.pkl")), \
         patch.object(indexer, "_HASH_FILE", str(idx_dir / "text_hash.txt")), \
         patch("embeddings.sentence_embeddings.embed_sentences", side_effect=_fake_embed):
        indexer.index_document("First clause. Second clause. Third clause. Fourth clause.")
    assert (idx_dir / "faiss.index").exists()


# ---------- persistent (Postgres/SQLite-backed) knowledge-base session state ----------

@pytest.fixture
def flask_app(db_session):
    """A minimal Flask app wired to webapp.state, sharing the same in-memory DB as db_session."""
    from flask import Flask
    from webapp import state as kb_state
    app = Flask(__name__)
    app.secret_key = "test"
    kb_state.init_app(app)
    return app


def test_kb_session_state_persists_across_requests(flask_app):
    from flask import session
    from rag.indexer import Chunk

    with flask_app.test_request_context("/"):
        session["kb_sid"] = "sid-1"
        from webapp.state import get_state
        s = get_state()
        s.raw_text = "hello world"
        s.processed = True
        c = Chunk("a clause")
        c.doc, c.page, c.label = "a.pdf", 3, "Page 3"
        s.chunks = [c]

    # a fresh request (new process would look the same): reload by sid, not by in-memory identity
    with flask_app.test_request_context("/"):
        session["kb_sid"] = "sid-1"
        from webapp.state import get_state
        reloaded = get_state()
        assert reloaded.raw_text == "hello world" and reloaded.processed
        assert reloaded.chunks[0].doc == "a.pdf" and reloaded.chunks[0].page == 3
        assert not reloaded._dirty          # a fresh load is not considered dirty


def test_kb_session_read_only_request_does_not_rewrite_row(flask_app, db_session):
    from flask import session
    with flask_app.test_request_context("/"):
        session["kb_sid"] = "sid-2"
        from webapp.state import get_state
        get_state().raw_text = "persist me"

    before = db_session.get(db.KBSessionRow, "sid-2").updated_at
    with flask_app.test_request_context("/"):
        session["kb_sid"] = "sid-2"
        from webapp.state import get_state
        get_state()   # read only, no mutation
    db_session.expire_all()
    after = db_session.get(db.KBSessionRow, "sid-2").updated_at
    assert before == after


def test_zero_retention_session_is_never_written_to_the_database(flask_app, db_session):
    from flask import session
    with flask_app.test_request_context("/"):
        session["kb_sid"] = "sid-3"
        from webapp.state import get_state
        s = get_state()
        s.zero_retention = True
        s.raw_text = "never persist this"

    assert db_session.get(db.KBSessionRow, "sid-3") is None   # nothing written at all

    with flask_app.test_request_context("/"):
        session["kb_sid"] = "sid-3"
        from webapp.state import get_state
        assert get_state().raw_text == "never persist this"   # still there, just in memory


def test_turning_on_zero_retention_purges_the_previously_saved_row(flask_app, db_session):
    from flask import session
    with flask_app.test_request_context("/"):
        session["kb_sid"] = "sid-4"
        from webapp.state import get_state
        get_state().raw_text = "saved first"
    assert db_session.get(db.KBSessionRow, "sid-4") is not None

    with flask_app.test_request_context("/"):
        session["kb_sid"] = "sid-4"
        from webapp.state import get_state
        get_state().zero_retention = True

    db_session.expire_all()
    assert db_session.get(db.KBSessionRow, "sid-4") is None
