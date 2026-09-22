# rag/citations.py
"""
Numbered-source citation helpers.
Sources are numbered once per answer; the LLM cites them as [1], [2]...,
and we verify afterwards that every cited number really exists.
"""
import re

_CITE_RE = re.compile(r"\[(\d{1,2})\]")


def number_sources(results: list, limit: int = 8) -> list[dict]:
    """De-duplicate hybrid_search results (by chunk_id) and number them from 1."""
    seen: set = set()
    sources: list[dict] = []
    for chunk, score, meta in results:
        key = meta.get("chunk_id", str(chunk))
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "n": len(sources) + 1, "doc": meta["doc_name"], "location": meta["location"],
            "score": score, "text": str(chunk),
        })
        if len(sources) == limit:
            break
    return sources


def build_context(sources: list[dict], max_chars: int = 3000) -> tuple[str, list[dict]]:
    """Render sources as '[n] doc — location' blocks. Returns (context, sources actually included)."""
    parts: list[str] = []
    used: list[dict] = []
    total = 0
    for s in sources:
        block = f"[{s['n']}] {s['doc']} — {s['location']}\n{s['text']}"
        if total + len(block) > max_chars and used:
            break
        parts.append(block)
        used.append(s)
        total += len(block)
    return "\n\n".join(parts), used


def verify_citations(answer: str, n_sources: int) -> dict:
    """Which [n] markers in the answer are valid, and which point at non-existent sources."""
    nums = [int(m) for m in _CITE_RE.findall(answer or "")]
    return {
        "cited":   sorted({n for n in nums if 1 <= n <= n_sources}),
        "invalid": sorted({n for n in nums if not 1 <= n <= n_sources}),
    }


def strip_invalid(answer: str, invalid: list[int]) -> str:
    """Remove markers that reference sources that were never provided."""
    if not invalid:
        return answer
    bad = set(invalid)
    return _CITE_RE.sub(lambda m: "" if int(m.group(1)) in bad else m.group(0), answer)


def confidence_label(top_score: float) -> str:
    """Retrieval-based confidence (deterministic — not self-reported by the model)."""
    if top_score >= 0.6:
        return "High"
    if top_score >= 0.4:
        return "Medium"
    return "Low"
