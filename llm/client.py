# llm/client.py
"""
Single Ollama chat client shared by every generative module.
Returns the reply text, or None on failure (callers fall back to rule-based output).
"""
import logging
import re
import time
from typing import TypeVar

import requests
from pydantic import BaseModel, ValidationError

from config import settings

log = logging.getLogger("lexi.llm")


def chat(system_prompt: str, user_message: str, max_tokens: int = 1000,
         model: str | None = None, timeout: int | None = None,
         temperature: float | None = None, schema: dict | None = None) -> str | None:
    payload = {
        "model"   : model or settings.ollama_model,
        "stream"  : False,
        "options" : {
            "num_predict": max_tokens,
            "temperature": settings.llm_temperature if temperature is None else temperature,
        },
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
    }
    if schema:
        payload["format"] = schema  # Ollama structured output: constrain reply to this JSON schema
    attempts = settings.llm_retries + 1
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.post(settings.ollama_url, json=payload,
                                 timeout=timeout or settings.llm_timeout)
            if resp.status_code == 200:
                return resp.json()["message"]["content"].strip()
            log.error("Ollama returned %s: %s", resp.status_code, resp.text[:200])
            if resp.status_code < 500:
                return None  # client error (e.g. model not pulled) — retrying won't help
        except requests.exceptions.ConnectionError:
            log.error("Ollama not reachable at %s. Start it with: ollama serve", settings.ollama_url)
            return None
        except Exception as e:
            log.error("Ollama call failed (attempt %d/%d): %s", attempt, attempts, e)
        if attempt < attempts:
            time.sleep(2 ** (attempt - 1))
    return None


def health_check() -> tuple[bool, str]:
    """Returns (ok, message) — is Ollama up and is the configured model pulled?"""
    base = settings.ollama_url.rsplit("/api/", 1)[0]
    try:
        r = requests.get(f"{base}/api/tags", timeout=3)
        r.raise_for_status()
        names = [m.get("name", "") for m in r.json().get("models", [])]
    except Exception:
        return False, "Ollama is not running. Start it with `ollama serve`."
    if not any(n == settings.ollama_model or n.split(":")[0] == settings.ollama_model for n in names):
        return False, f"Model `{settings.ollama_model}` not found. Run `ollama pull {settings.ollama_model}`."
    return True, f"Ollama ready ({settings.ollama_model})."


T = TypeVar("T", bound=BaseModel)


def chat_json(system_prompt: str, user_message: str, model_cls: type[T], max_tokens: int = 2000,
              **kwargs) -> T | None:
    """
    Ask for output constrained to `model_cls`'s JSON schema and return a validated instance,
    or None if the model is offline / the reply can't be validated.
    """
    raw = chat(system_prompt, user_message, max_tokens=max_tokens,
               schema=model_cls.model_json_schema(), **kwargs)
    if not raw:
        return None
    try:
        return model_cls.model_validate_json(raw)
    except ValidationError:
        pass
    # repair: strip code fences / surrounding prose and retry once
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return model_cls.model_validate_json(match.group())
        except ValidationError as e:
            log.error("Structured reply failed validation: %s", str(e)[:200])
    return None
