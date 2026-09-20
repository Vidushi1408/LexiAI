# audit/log.py
"""
Append-only, hash-chained audit log (JSON Lines).

Each entry stores the hash of the previous entry, so editing or deleting any past line
breaks the chain and `verify()` reports where. Entries hold metadata only — never document
text. Query text is stored as a hash unless LEXI_AUDIT_LOG_QUERIES=1.
"""
import csv, hashlib, io, json, os, threading
from datetime import datetime, timezone

from config import settings

_lock = threading.Lock()
GENESIS = "0" * 64
FIELDS = ["seq", "ts", "user", "action", "details", "prev_hash", "hash"]


def _digest(entry: dict) -> str:
    body = {k: entry[k] for k in FIELDS if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _read(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def fingerprint(text: str) -> str:
    """Short stable hash so a query can be referenced without storing it."""
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def record(action: str, user: str = "anonymous", path: str | None = None, **details) -> dict:
    path = path or settings.audit_log_path
    with _lock:
        entries = _read(path)
        entry = {
            "seq": len(entries) + 1,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "user": user, "action": action, "details": details,
            "prev_hash": entries[-1]["hash"] if entries else GENESIS,
        }
        entry["hash"] = _digest(entry)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def verify(path: str | None = None) -> tuple[bool, str]:
    """Returns (ok, message). On failure the message names the first broken entry."""
    entries = _read(path or settings.audit_log_path)
    prev = GENESIS
    for i, e in enumerate(entries, 1):
        if e["seq"] != i or e["prev_hash"] != prev or e["hash"] != _digest(e):
            return False, f"Audit log tampered or corrupted at entry #{i}."
        prev = e["hash"]
    return True, f"Audit log intact ({len(entries)} entries)."


def read(path: str | None = None, limit: int | None = None) -> list[dict]:
    entries = _read(path or settings.audit_log_path)
    return entries[-limit:] if limit else entries


def export_csv(path: str | None = None) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["seq", "timestamp", "user", "action", "details", "hash"])
    for e in _read(path or settings.audit_log_path):
        w.writerow([e["seq"], e["ts"], e["user"], e["action"], json.dumps(e["details"], ensure_ascii=False), e["hash"]])
    return buf.getvalue()
