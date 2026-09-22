# webapp/state.py
"""
Per-browser-session knowledge base state.

Flask requests are stateless, so the uploaded text, FAISS index and generated results need
somewhere to live between requests. They are kept server-side in this process's memory, keyed by
a random id stored in the user's signed session cookie (never the data itself, and never the FAISS
index, which isn't JSON-serialisable).

Limitation: this only works for a single web process. Running more than one gunicorn worker (or
more than one host) means a request can land on a worker that never saw this browser's upload.
Fix (M4): move this to Redis/a database, keyed the same way, when scaling beyond one process.
"""
import threading
import uuid
from dataclasses import dataclass, field

from flask import session

from config import settings


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
    zero_retention: bool = settings.zero_retention
    last_audited_question: str | None = None
    qa_confidences: list = field(default_factory=list)  # real retrieval confidence per question asked
    flat_ingestion: list = field(default_factory=list)  # doc names ingested without real per-page provenance

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
        self.last_audited_question = None
        self.qa_confidences = []
        self.flat_ingestion = []


_lock = threading.Lock()
_STORE: dict[str, KBState] = {}


def get_state() -> KBState:
    """The current browser session's knowledge-base state, creating one if this is a new session."""
    sid = session.get("kb_sid")
    if not sid:
        sid = uuid.uuid4().hex
        session["kb_sid"] = sid
    with _lock:
        return _STORE.setdefault(sid, KBState())


def drop_state() -> None:
    """Free this browser session's state (called on logout so memory doesn't grow unbounded)."""
    sid = session.pop("kb_sid", None)
    if sid:
        with _lock:
            _STORE.pop(sid, None)
