# generative/quote_check.py
"""Verify that a quote the LLM produced really appears in the source text."""
import re
from difflib import SequenceMatcher


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[\"'“”‘’]", "", s or "")).strip().lower()


def quote_in_text(quote: str, text: str, min_len: int = 15, tolerance: float = 0.85) -> bool:
    """
    True if `quote` appears in `text` (case/whitespace/quote-mark insensitive), or if a single
    contiguous run covering at least `tolerance` of the quote does (tolerates small edits).
    """
    q, t = _norm(quote), _norm(text)
    if len(q) < min_len:
        return False
    if q in t:
        return True
    block = SequenceMatcher(None, t, q, autojunk=False).find_longest_match(0, len(t), 0, len(q))
    return block.size >= tolerance * len(q)
