# utils/upload_guard.py
"""
Validate uploads before any parser touches them: extension allow-list, size limits,
magic-byte check (the content must match the extension), and zip-bomb limits for Office files.
"""
import io, os, re, zipfile

from config import settings

ALLOWED = {".pdf", ".docx", ".xlsx", ".xls", ".pptx", ".csv", ".txt", ".md", ".eml", ".mp3", ".wav"}
AUDIO = {".mp3", ".wav"}
OOXML = {".docx": "word/", ".xlsx": "xl/", ".pptx": "ppt/"}
TEXT = {".csv", ".txt", ".md", ".eml"}

MAX_ZIP_ENTRIES = 5000
MAX_UNCOMPRESSED = 300 * 1024 * 1024
MAX_RATIO = 100


def safe_filename(name: str, max_len: int = 120) -> str:
    """Basename only, control characters removed — safe to log and display."""
    base = os.path.basename((name or "").replace("\\", "/"))
    base = re.sub(r"[\x00-\x1f\x7f]", "", base).strip()
    return (base or "unnamed")[:max_len]


def _check_zip(data: bytes, ext: str) -> str | None:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return "File is not a valid Office document."
    infos = zf.infolist()
    if len(infos) > MAX_ZIP_ENTRIES:
        return "Office file contains too many parts."
    total = sum(i.file_size for i in infos)
    if total > MAX_UNCOMPRESSED or (len(data) and total / len(data) > MAX_RATIO):
        return "Office file expands to an unsafe size (possible zip bomb)."
    for i in infos:
        if i.filename.startswith(("/", "\\")) or ".." in i.filename.split("/"):
            return "Office file contains unsafe paths."
    names = {i.filename for i in infos}
    if "[Content_Types].xml" not in names or not any(n.startswith(OOXML[ext]) for n in names):
        return f"File content does not match its {ext} extension."
    return None


def validate_upload(name: str, data: bytes) -> tuple[bool, str]:
    """Returns (ok, reason). Reason is user-presentable when not ok."""
    ext = os.path.splitext(safe_filename(name))[1].lower()
    if ext not in ALLOWED:
        return False, f"File type {ext or '(none)'} is not supported."
    if not data:
        return False, "File is empty."
    limit_mb = settings.max_audio_mb if ext in AUDIO else settings.max_upload_mb
    if len(data) > limit_mb * 1024 * 1024:
        return False, f"File exceeds the {limit_mb} MB limit."

    if ext == ".pdf":
        if not data.lstrip()[:5] == b"%PDF-":
            return False, "File content does not match its .pdf extension."
    elif ext in OOXML:
        if data[:4] != b"PK\x03\x04":
            return False, f"File content does not match its {ext} extension."
        problem = _check_zip(data, ext)
        if problem:
            return False, problem
    elif ext == ".xls":
        if data[:8] != bytes.fromhex("D0CF11E0A1B11AE1"):
            return False, "File content does not match its .xls extension."
    elif ext == ".mp3":
        if not (data[:3] == b"ID3" or (data[0] == 0xFF and data[1] & 0xE0 == 0xE0)):
            return False, "File content does not match its .mp3 extension."
    elif ext == ".wav":
        if not (data[:4] == b"RIFF" and data[8:12] == b"WAVE"):
            return False, "File content does not match its .wav extension."
    elif ext in TEXT:
        if b"\x00" in data[:8192]:
            return False, "File looks binary, not text."
    return True, "ok"
