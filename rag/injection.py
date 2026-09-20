# rag/injection.py
"""
Heuristic scan for prompt-injection attempts hidden in uploaded documents.
This only WARNS; the real defence is that every LLM call is told document text is untrusted data
(see llm.client.UNTRUSTED_NOTICE) and no tool or action is ever driven by document content.
"""
import re

_PATTERNS = {
    "override instructions": r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|prompts?|rules)",
    "disregard instructions": r"disregard (all |any |the )?(previous|prior|above|earlier|system)",
    "role hijack": r"you are now (a|an|the)\b|act as (a|an|the) (?!party|guarantor)",
    "reveal prompt": r"(reveal|show|print|repeat) (your|the) (system )?(prompt|instructions)",
    "fake system message": r"(^|\n)\s*(system|assistant)\s*:",
    "forced verdict": r"(mark|set|rate|report) (all |every |this )?(\w+ )?(as |to )?(pass|compliant|approved)\b.{0,30}(regardless|always|no matter)",
    "output manipulation": r"(do not|don'?t) (mention|tell|reveal|cite)",
}
_COMPILED = {k: re.compile(v, re.IGNORECASE) for k, v in _PATTERNS.items()}


def scan(text: str) -> list[str]:
    """Labels of suspicious patterns found in `text` (empty list if clean)."""
    return [label for label, rx in _COMPILED.items() if rx.search(text or "")]
