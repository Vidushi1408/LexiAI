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


settings = Settings()
