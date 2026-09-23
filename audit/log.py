# audit/log.py
"""
Append-only, hash-chained audit log — the `audit_log` table (db.py), Postgres in production.

Each entry stores the hash of the previous entry, so editing or deleting any past row breaks
the chain and `verify()` reports where. Entries hold metadata only — never document text. Query
text is stored as a hash unless LEXI_AUDIT_LOG_QUERIES=1.
"""
import csv, hashlib, io, json, threading
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from db import AuditEntry, new_session

_lock = threading.Lock()
GENESIS = "0" * 64
FIELDS = ["seq", "ts", "user", "action", "details", "prev_hash", "hash"]


def _digest(entry: dict) -> str:
    body = {k: entry[k] for k in FIELDS if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _as_dict(row: AuditEntry) -> dict:
    return {"seq": row.seq, "ts": row.ts, "user": row.user, "action": row.action,
            "details": row.details, "prev_hash": row.prev_hash, "hash": row.hash}


def _session(session: Session | None):
    return (session, False) if session is not None else (new_session(), True)


def fingerprint(text: str) -> str:
    """Short stable hash so a query can be referenced without storing it."""
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def record(action: str, user: str = "anonymous", session: Session | None = None, **details) -> dict:
    s, owns = _session(session)
    try:
        with _lock:
            last = s.query(AuditEntry).order_by(AuditEntry.seq.desc()).first()
            entry = {
                "seq": (last.seq if last else 0) + 1,
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "user": user, "action": action, "details": details,
                "prev_hash": last.hash if last else GENESIS,
            }
            entry["hash"] = _digest(entry)
            s.add(AuditEntry(**entry))
            s.commit()
        return entry
    finally:
        if owns:
            s.close()


def verify(session: Session | None = None) -> tuple[bool, str]:
    """Returns (ok, message). On failure the message names the first broken entry."""
    s, owns = _session(session)
    try:
        rows = s.query(AuditEntry).order_by(AuditEntry.seq).all()
        prev, count = GENESIS, 0
        for i, row in enumerate(rows, 1):
            e = _as_dict(row)
            if e["seq"] != i or e["prev_hash"] != prev or e["hash"] != _digest(e):
                return False, f"Audit log tampered or corrupted at entry #{i}."
            prev, count = e["hash"], count + 1
        return True, f"Audit log intact ({count} entries)."
    finally:
        if owns:
            s.close()


def read(session: Session | None = None, limit: int | None = None) -> list[dict]:
    s, owns = _session(session)
    try:
        q = s.query(AuditEntry).order_by(AuditEntry.seq)
        if limit:
            total = s.query(func.count(AuditEntry.seq)).scalar()
            q = q.offset(max(0, total - limit))
        return [_as_dict(row) for row in q.all()]
    finally:
        if owns:
            s.close()


def export_csv(session: Session | None = None) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["seq", "timestamp", "user", "action", "details", "hash"])
    for e in read(session):
        w.writerow([e["seq"], e["ts"], e["user"], e["action"], json.dumps(e["details"], ensure_ascii=False), e["hash"]])
    return buf.getvalue()
