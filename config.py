# config.py
"""
Central configuration for Lexi AI.
Values come from environment variables (or a local .env file) with sane defaults.
"""
import os
import secrets
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _load_or_create_secret_key(path: str) -> str:
    """
    LEXI_SECRET_KEY, else a key persisted to disk so it survives restarts and is shared by every
    gunicorn worker (a key regenerated per-process would silently invalidate sessions/CSRF tokens
    across workers). Set LEXI_SECRET_KEY explicitly for a multi-host deployment.
    """
    env = os.getenv("LEXI_SECRET_KEY")
    if env:
        return env
    if os.path.exists(path):
        return open(path, encoding="utf-8").read().strip()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    key = secrets.token_hex(32)
    try:
        fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(key)
        return key
    except FileExistsError:
        return open(path, encoding="utf-8").read().strip()  # another worker created it first


@dataclass(frozen=True)
class Settings:
    ollama_url:     str   = os.getenv("LEXI_OLLAMA_URL", "http://localhost:11434/api/chat")
    ollama_model:   str   = os.getenv("LEXI_OLLAMA_MODEL", "llama3.2:3b")
    llm_timeout:    int   = int(os.getenv("LEXI_LLM_TIMEOUT", "120"))
    llm_retries:    int   = int(os.getenv("LEXI_LLM_RETRIES", "2"))
    llm_temperature: float = float(os.getenv("LEXI_LLM_TEMPERATURE", "0.3"))
    min_relevance:  float = float(os.getenv("LEXI_MIN_RELEVANCE", "0.3"))  # min vector similarity, else answer "not found"
    audit_log_queries: bool = os.getenv("LEXI_AUDIT_LOG_QUERIES", "0") == "1"   # store query text (default: hash only)
    zero_retention: bool = os.getenv("LEXI_ZERO_RETENTION", "0") == "1"       # nothing written to disk
    auth_enabled:   bool = os.getenv("LEXI_AUTH_ENABLED", "1") == "1"         # set 0 only for local demos
    max_upload_mb:  int = int(os.getenv("LEXI_MAX_UPLOAD_MB", "25"))
    max_audio_mb:   int = int(os.getenv("LEXI_MAX_AUDIO_MB", "100"))
    secret_key:     str = _load_or_create_secret_key(
        os.getenv("LEXI_SECRET_KEY_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "auth", ".flask_secret_key")))
    session_cookie_secure: bool = os.getenv("LEXI_SESSION_COOKIE_SECURE", "1") == "1"  # 0 only for local http:// dev

    # Postgres in production (docker-compose and CI both provide one); falls back to a local
    # SQLite file so `python app.py` still works with zero setup for local development.
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "lexi.db"))


settings = Settings()
