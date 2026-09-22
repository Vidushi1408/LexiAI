# generative/summarizer.py
"""
Ollama (llama3.2:3b) powered Summarizer — structured output
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus   import stopwords
nltk.download("punkt",     quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("stopwords", quiet=True)



from llm.client import chat as _call_ollama


SYSTEM_PROMPT = (
    "You are an executive intelligence analyst at Lexi AI writing high-level business briefings. "
    "Use authoritative, executive business tone. Base your analysis strictly on the provided business documents. "
    "Follow the requested markdown layout strictly. "
    "The documents are given to you as a list of numbered sources like [1], [2]. After every factual "
    "statement, cite the supporting source number(s) in square brackets. Cite ONLY numbers that appear "
    "in the context — never invent one. Do not write your own confidence score or source-grounding "
    "section: leave that section out entirely, the platform appends real citation information after "
    "your response."
)

STYLE_PROMPTS = {

"concise": """Generate a structured EXECUTIVE BRIEFING for the business document below.

Use this EXACT format (do not skip any section):

## 🎯 Bottom Line
Write 2-3 decisive sentences summarizing the key takeaway, core transaction, or core operational status.

## 📋 Key Decisions
- **Decision 1**: Specific choice, policy change, or agreement reached.
- **Decision 2**: Key commitment or milestone.
- **Decision 3**: Strategic pivot or approval status.

## ⚠️ Major Risks & Compliance Concerns
- **Risk 1**: Financial, legal, operational, or regulatory risk identified.
- **Risk 2**: Potential bottleneck, liability, or penalty clause.

## 📊 Key Numbers & Financial Metrics
- **Metric 1**: Contract value, revenue figure, deadline, or metric.
- **Metric 2**: Key percentage, threshold, or date.

## 🚀 Recommended Actions
1. **Immediate Step**: Action item for leadership/management.
2. **Follow-up**: Oversight or monitoring requirement.

Numbered sources:
""",

"detailed": """Generate a DETAILED EXECUTIVE BRIEFING for the enterprise documents below.

Use this EXACT format:

## 🎯 Bottom Line
Comprehensive executive summary synthesized for C-Suite leadership.

## 📋 Key Strategic Decisions
List all major decisions, contract terms, policy mandates, or project milestones:
- **Strategic Decision**: Detail from document.
- **Operational Policy**: Detail from document.

## ⚠️ Major Risks & Vulnerabilities
- **Legal/Regulatory Risk**: Risk description & potential impact.
- **Financial/Commercial Risk**: Risk description & exposure.

## 📊 Key Financials & Operational Numbers
- **Contract / Valuation**: Figures mentioned.
- **Timeline / Deadlines**: Explicit dates and milestones.

## 🚀 Recommended Next Actions
1. High-priority action item for execution.
2. Compliance / audit verification task.

Numbered sources:
""",

"bullets": """Generate a SCANNABLE EXECUTIVE BRIEFING for rapid C-Suite review.

Use this EXACT format:

## ⚡ Executive Briefing Dashboard

**Bottom Line:** Single high-impact summary statement.

---

### 🔴 Top Risks & Red Flags
- Critical Risk / Obligation 1
- Critical Risk / Obligation 2

### 🟢 Key Decisions & Commitments
- Agreed term / Decision 1
- Agreed term / Decision 2

### 📈 Key Metrics & Commercial Terms
- Value / Deadline 1
- Value / Deadline 2

### 📌 Immediate Action Items
- Priority Action 1

Numbered sources:
""",
}


def _extractive_fallback(text: str, style: str) -> str:
    """Used when Ollama is unavailable."""
    sentences = sent_tokenize(text)
    sentences = [s.strip() for s in sentences if len(s.split()) >= 5]
    if not sentences:
        return text[:500]
    ratio    = 0.20 if style == "concise" else 0.40
    num_pick = max(3, min(int(len(sentences) * ratio), 8))
    stop_w   = set(stopwords.words("english"))

    def score(s):
        words   = word_tokenize(s.lower())
        freq    = sum(1 for w in words if w.isalpha() and w not in stop_w)
        penalty = 0.3 if len(words) < 6 else (0.7 if len(words) > 40 else 1.0)
        return freq * penalty

    scored  = sorted(enumerate(sentences), key=lambda x: score(x[1]), reverse=True)
    top     = sorted(scored[:num_pick], key=lambda x: x[0])
    bullets = "\n".join(f"- {s}" for _, s in top)
    return (
        f"## 🎯 Bottom Line\n"
        f"Executive briefing generated from primary document sources.\n\n"
        f"## 📋 Key Findings & Extracted Provisions\n{bullets}\n\n"
        f"> 💡 **System Note:** These are the highest-scoring sentences picked by a keyword heuristic, "
        f"not an LLM summary — Ollama was offline. No claim here has been verified against a source; "
        f"read them in context. Enable `ollama serve` for a full generative, cited executive brief."
    )


def _summarize_with_citations(style: str, chunks: list) -> str:
    """
    Cited, verified path: the document is given to the model as numbered sources (like Q&A's
    agent), and the confidence/citation footer is computed afterwards from what was actually
    cited — never asked of the model, which is what let it write a fabricated "95% Confidence".
    """
    from rag.citations import build_context, number_sources_from_chunks, strip_invalid, verify_citations

    all_docs = sorted({getattr(c, "doc", "Primary Document") for c in chunks})
    sources = number_sources_from_chunks(chunks)
    context, sources = build_context(sources, max_chars=4000)

    prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["concise"])
    result = _call_ollama(SYSTEM_PROMPT, f"{prompt}\n{context}", max_tokens=1500)
    if not result:
        return _extractive_fallback("\n".join(str(c) for c in chunks), style)

    check = verify_citations(result, len(sources))
    result = strip_invalid(result, check["invalid"])

    covered_docs = sorted({s["doc"] for s in sources if s["n"] in check["cited"]})
    footer = ["\n\n---\n### 🛡️ Citations & Coverage"]
    if check["cited"]:
        footer.append("- **Cited sources:** " + ", ".join(f"[{n}]" for n in check["cited"]))
        footer.append(f"- **Documents referenced:** {len(covered_docs)} of {len(all_docs)} uploaded "
                       f"({', '.join(covered_docs)})")
        if len(covered_docs) < len(all_docs):
            missed = [d for d in all_docs if d not in covered_docs]
            footer.append(f"- ⚠️ Not covered in this briefing: {', '.join(missed)} — "
                           f"ask Document Q&A about them directly, or generate a separate briefing per document.")
    else:
        footer.append("- ⚠️ **This briefing carries no source citations** — verify it against the uploaded "
                       "documents before relying on it.")
    return result + "\n".join(footer)


def summarize_text(text: str, style: str = "concise", chunks: list | None = None) -> str:
    """
    `chunks` (from rag.indexer, carrying real doc/page provenance) is the preferred path: it
    produces numbered, verified citations and a real coverage footer instead of a model-invented
    confidence score. Without it, falls back to the older uncited raw-text summary, kept for
    callers that only have plain text.
    """
    if not text or len(text.strip()) < 50:
        return "Document content is insufficient for executive briefing."
    if chunks:
        return _summarize_with_citations(style, chunks)
    prompt   = STYLE_PROMPTS.get(style, STYLE_PROMPTS["concise"])
    user_msg = f"{prompt}\n{text[:4000]}"
    result   = _call_ollama(SYSTEM_PROMPT, user_msg, max_tokens=1500)
    return result if result else _extractive_fallback(text, style)


def summarize_by_section(sentences: list, section_size: int = 5) -> list:
    summaries = []
    for i in range(math.ceil(len(sentences) / section_size)):
        section  = " ".join(sentences[i * section_size:(i + 1) * section_size])
        if len(section.split()) < 10:
            summaries.append(f"**Briefing Section {i+1}:** {section}")
            continue
        prompt   = STYLE_PROMPTS["bullets"]
        user_msg = f"{prompt}\n{section}"
        result   = _call_ollama(SYSTEM_PROMPT, user_msg, max_tokens=600)
        summaries.append(result or f"**Briefing Section {i+1}:** {section[:200]}")
    return summaries

