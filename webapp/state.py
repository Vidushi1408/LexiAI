# webapp/state.py
"""
Per-browser-session knowledge base state.

Flask requests are stateless, so the uploaded text, FAISS index and generated results need
somewhere to live between requests. A session's state lives in the `kb_sessions` table (db.py) —
Postgres in production — keyed by a random id stored in the user's signed session cookie (never
the data itself). This is what lets the app run correctly behind more than one gunicorn worker or
host, unlike the in-memory dict this module used before M4.

Zero-retention is the one deliberate exception: a session with it on is kept ONLY in this
process's memory and is never written to the database, matching the promise the feature makes.
The unavoidable trade-off is that a zero-retention session only behaves correctly pinned to one
worker/host — there is no durable, shared store that isn't itself a form of retention. Multi-worker
zero-retention would need a shared *ephemeral* store (e.g. Redis with persistence disabled), which
is out of scope until the job-queue work happens.

State is loaded on first access per request (cached on `flask.g`) and saved automatically after
the request via `init_app`'s teardown hook — a view mutates `state.x = ...` and does not need to
call anything to persist it. A dirty flag avoids writing on every read-only request.
"""
import threading
import uuid
from dataclasses import dataclass, field

import numpy as np
from flask import g, session

from config import settings
from db import KBSessionRow, new_session
from rag.indexer import Chunk

HISTORY_LIMIT = 10  # oldest entries drop off past this, per feature, per knowledge base


@dataclass
class KBState:
    raw_text: str | None = None
    file_name: str | None = None
    pages: list | None = None
    processed: bool = False
    faiss_index: object = None
    chunks: list = field(default_factory=list)
    pipeline_result: dict | None = None
    summary_result: str | None = None
    compliance_result: list | None = None
    entities_result: dict | None = None
    action_items_result: list | None = None
    # Past runs for the four "generate and keep the latest" features, oldest first, capped at
    # HISTORY_LIMIT. The singular fields above stay as "the latest run" (== history[-1] once
    # append_history has been called) so existing reads of them are unaffected.
    briefing_history: list = field(default_factory=list)
    compliance_history: list = field(default_factory=list)
    entities_history: list = field(default_factory=list)
    action_items_history: list = field(default_factory=list)
    zero_retention: bool = settings.zero_retention
    last_audited_question: str | None = None
    qa_confidences: list = field(default_factory=list)  # real retrieval confidence per question asked
    flat_ingestion: list = field(default_factory=list)  # doc names ingested without real per-page provenance
    _dirty: bool = field(default=False, repr=False, compare=False)

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if name != "_dirty":
            object.__setattr__(self, "_dirty", True)

    def append_history(self, attr: str, entry: dict) -> None:
        """Add a timestamped run to one of the four history lists, oldest-first, capped."""
        history = getattr(self, attr)
        setattr(self, attr, (history + [entry])[-HISTORY_LIMIT:])

    def clear_documents(self) -> None:
        self.raw_text = None
        self.file_name = None
        self.pages = None
        self.processed = False
        self.faiss_index = None
        self.chunks = []
        self.pipeline_result = None
        self.summary_result = None
        self.compliance_result = None
        self.entities_result = None
        self.action_items_result = None
        # A fresh set of documents starts a fresh history — the old runs were about a different
        # knowledge base and would be misleading shown alongside the new one.
        self.briefing_history = []
        self.compliance_history = []
        self.entities_history = []
        self.action_items_history = []
        self.last_audited_question = None
        self.qa_confidences = []
        self.flat_ingestion = []


_lock = threading.Lock()
_MEMORY_STORE: dict[str, KBState] = {}   # zero-retention sessions only — never touches the database


def _serialize_chunks(chunks: list) -> list[dict]:
    return [{"text": str(c), "doc": getattr(c, "doc", "Primary Document"),
             "page": getattr(c, "page", None), "label": getattr(c, "label", "")} for c in chunks]


def _deserialize_chunks(data: list | None) -> list:
    chunks = []
    for d in data or []:
        c = Chunk(d["text"])
        c.doc, c.page, c.label = d.get("doc", "Primary Document"), d.get("page"), d.get("label", "")
        chunks.append(c)
    return chunks


def _row_to_state(row: KBSessionRow) -> KBState:
    index = None
    if row.faiss_index:
        import faiss
        index = faiss.deserialize_index(np.frombuffer(row.faiss_index, dtype=np.uint8))
    return KBState(
        raw_text=row.raw_text, file_name=row.file_name, pages=row.pages, processed=bool(row.processed),
        faiss_index=index, chunks=_deserialize_chunks(row.chunks),
        pipeline_result=row.pipeline_result, summary_result=row.summary_result,
        compliance_result=row.compliance_result, entities_result=row.entities_result,
        action_items_result=row.action_items_result, zero_retention=bool(row.zero_retention),
        last_audited_question=row.last_audited_question, qa_confidences=row.qa_confidences or [],
        flat_ingestion=row.flat_ingestion or [],
        briefing_history=row.briefing_history or [], compliance_history=row.compliance_history or [],
        entities_history=row.entities_history or [], action_items_history=row.action_items_history or [],
    )


def _state_fields(state: KBState) -> dict:
    index_bytes = None
    if state.faiss_index is not None:
        import faiss
        index_bytes = faiss.serialize_index(state.faiss_index).tobytes()
    return dict(
        raw_text=state.raw_text, file_name=state.file_name, pages=state.pages, processed=state.processed,
        faiss_index=index_bytes, chunks=_serialize_chunks(state.chunks),
        pipeline_result=state.pipeline_result, summary_result=state.summary_result,
        compliance_result=state.compliance_result, entities_result=state.entities_result,
        action_items_result=state.action_items_result, zero_retention=state.zero_retention,
        last_audited_question=state.last_audited_question, qa_confidences=state.qa_confidences,
        flat_ingestion=state.flat_ingestion,
        briefing_history=state.briefing_history, compliance_history=state.compliance_history,
        entities_history=state.entities_history, action_items_history=state.action_items_history,
    )


def _current_sid() -> str:
    """Browser sessions get a random per-tab id in a signed cookie. An API-key caller has no
    cookie jar to rely on, so it gets one stable slot per account instead — every call with the
    same key sees the same knowledge base, no cookie handling required."""
    api_user = getattr(g, "api_user", None)
    if api_user:
        return f"api-{api_user['username']}"
    sid = session.get("kb_sid")
    if not sid:
        sid = uuid.uuid4().hex
        session["kb_sid"] = sid
    return sid


def get_state() -> KBState:
    """The current session's (browser tab's, or API account's) knowledge-base state, loading it
    once per request."""
    sid = _current_sid()

    if getattr(g, "_kb_sid", None) == sid and getattr(g, "_kb_state", None) is not None:
        return g._kb_state

    with _lock:
        cached = _MEMORY_STORE.get(sid)
    if cached is not None:
        state = cached
    else:
        db = new_session()
        try:
            row = db.get(KBSessionRow, sid)
            state = _row_to_state(row) if row else KBState()
        finally:
            db.close()

    state._dirty = False
    g._kb_sid, g._kb_state = sid, state
    return state


def _save_state(sid: str, state: KBState) -> None:
    if state.zero_retention:
        with _lock:
            _MEMORY_STORE[sid] = state
        _delete_row(sid)  # purge anything persisted before zero-retention was switched on
        return

    with _lock:
        _MEMORY_STORE.pop(sid, None)
    db = new_session()
    try:
        row = db.get(KBSessionRow, sid)
        fields = _state_fields(state)
        if row:
            for k, v in fields.items():
                setattr(row, k, v)
        else:
            db.add(KBSessionRow(sid=sid, **fields))
        db.commit()
    finally:
        db.close()
    state._dirty = False


def _delete_row(sid: str) -> None:
    db = new_session()
    try:
        row = db.get(KBSessionRow, sid)
        if row:
            db.delete(row)
            db.commit()
    finally:
        db.close()


def drop_state() -> None:
    """Free this browser session's state (called on logout)."""
    sid = session.pop("kb_sid", None)
    if not sid:
        return
    with _lock:
        _MEMORY_STORE.pop(sid, None)
    _delete_row(sid)
    if getattr(g, "_kb_sid", None) == sid:
        g._kb_state = None


def init_app(app) -> None:
    """Persist the current request's knowledge-base state after every request that changed it."""
    @app.teardown_appcontext
    def _persist_kb_state(exc):
        sid, state = getattr(g, "_kb_sid", None), getattr(g, "_kb_state", None)
        if sid and state is not None and state._dirty and exc is None:
            _save_state(sid, state)
