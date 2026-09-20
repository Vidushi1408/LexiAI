# config.py
"""
Central configuration for Lexi AI.
Values come from environment variables (or a local .env file) with sane defaults.
"""
import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    ollama_url:     str   = os.getenv("LEXI_OLLAMA_URL", "http://localhost:11434/api/chat")
    ollama_model:   str   = os.getenv("LEXI_OLLAMA_MODEL", "llama3.2:3b")
    llm_timeout:    int   = int(os.getenv("LEXI_LLM_TIMEOUT", "120"))
    llm_retries:    int   = int(os.getenv("LEXI_LLM_RETRIES", "2"))
    llm_temperature: float = float(os.getenv("LEXI_LLM_TEMPERATURE", "0.3"))
    min_relevance:  float = float(os.getenv("LEXI_MIN_RELEVANCE", "0.3"))  # min vector similarity, else answer "not found"
    audit_log_path: str = os.getenv("LEXI_AUDIT_LOG", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "audit", "audit.jsonl"))
    audit_log_queries: bool = os.getenv("LEXI_AUDIT_LOG_QUERIES", "0") == "1"   # store query text (default: hash only)
    zero_retention: bool = os.getenv("LEXI_ZERO_RETENTION", "0") == "1"       # nothing written to disk
    auth_enabled:   bool = os.getenv("LEXI_AUTH_ENABLED", "1") == "1"         # set 0 only for local demos
    users_path:     str = os.getenv("LEXI_USERS_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "auth", "users.json"))
    max_upload_mb:  int = int(os.getenv("LEXI_MAX_UPLOAD_MB", "25"))
    max_audio_mb:   int = int(os.getenv("LEXI_MAX_AUDIO_MB", "100"))


settings = Settings()
