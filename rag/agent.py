# rag/agent.py
"""
Multi-Tool Study Agent — Ollama (llama3.2:3b) powered
Works synchronously — fully compatible with Streamlit.
No API key needed. Runs locally via Ollama.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.retriever import is_query_answerable
from rag.indexer   import load_index
from llm.client    import chat as _call_ollama
from config        import settings
from rag.citations import number_sources, build_context, verify_citations, strip_invalid, confidence_label


# ── Prompts ───────────────────────────────────────────────────

ANSWER_SYSTEM = """You are an Enterprise Intelligence Analyst at Lexi AI answering executive & legal questions.

Give structured, precise, and authoritative answers using ONLY the provided document context.

OUTPUT STRUCTURE:
**Executive Answer:** [1-2 sentence direct, decisive answer]

### 📌 Analysis & Explanation
[3-4 detailed sentences synthesized directly from the retrieved document chunks]

### 🔑 Key Findings & Provisions
- **Point 1**: Specific detail from document
- **Point 2**: Specific detail from document
- **Point 3**: Specific detail from document


STRICT RULES:
- The context is a list of numbered sources like [1], [2]. After EVERY factual statement, cite the supporting source number(s) in square brackets, e.g. "Notice is 90 days [2]."
- Cite ONLY numbers that appear in the context. NEVER invent a source or a number. Do not write a separate sources list.
- Answer ONLY from the provided document context.
- If the topic is not covered in the context, explicitly state: "**Not Found in Document Knowledge Base.** This topic is not covered in the uploaded enterprise documents."
"""


import logging
log = logging.getLogger("lexi.rag.agent")


def _detect_format(question: str) -> str:
    """Detect the best answer format from the question text."""
    q = question.lower()
    if any(w in q for w in ["what is", "define", "definition of", "meaning of"]):
        return "definition"
    if any(w in q for w in ["how does", "how do", "steps", "process", "explain how"]):
        return "process"
    if any(w in q for w in ["difference", "compare", "vs", "versus", "distinguish"]):
        return "comparison"
    return "general"


def _generate_answer(question: str, context: str) -> str:
    """Call Ollama to generate a structured answer from retrieved context."""
    user_msg = (
        f"Context from uploaded enterprise documents:\n\n{context}\n\n"
        f"---\n\n"
        f"Question: {question}\n\n"
        f"Generate a structured business answer using ONLY the context above."
    )
    result = _call_ollama(ANSWER_SYSTEM, user_msg, max_tokens=1000)
    return result or "**Could not generate answer.** Ollama engine offline — try `ollama serve`."


def run_agent(question: str, index=None, chunks: list = None) -> dict:
    """
    Main document intelligence agent: retrieve -> numbered sources -> cited answer -> verify.
    Returns answer, numbered `citations` (each flagged `cited` if the answer references it),
    and `citation_check` {"cited": [...], "invalid": [...]}.
    """
    if index is None or chunks is None:
        index, chunks = load_index()

    def _refusal(msg: str) -> dict:
        return {"answer": msg, "tool_calls": [], "answerable": False, "question": question,
                "citations": [], "citation_check": {"cited": [], "invalid": []}}

    if index is None:
        return _refusal("**No document loaded.**\n\nPlease upload and process enterprise documents in the Knowledge Base first.")

    from rag.retriever import hybrid_search, answer_confidence

    # ── Step 1: retrieve, and refuse when nothing relevant enough was found ──
    tool_log = []
    log.info(f"[AGENT] 🔍 hybrid_search: '{question[:60]}'")
    results = hybrid_search(question, index, chunks, top_k=5)
    tool_log.append({"tool": "hybrid_search", "input": {"query": question}, "hits": len(results)})

    if not is_query_answerable(results, threshold=settings.min_relevance):
        return _refusal(
            "**Not found in Enterprise Knowledge Base.**\n\n"
            "This query does not match any information in the uploaded business documents."
        )

    # ── Step 2: second search for comparison questions ──
    q_lower = question.lower()
    if any(w in q_lower for w in ["difference", "compare", "vs", "versus", "distinguish"]):
        words = [w for w in question.split() if len(w) > 4]
        second_query = " ".join(words[-3:]) if len(words) > 3 else question
        log.info(f"[AGENT] 🔍 hybrid_search_secondary: '{second_query[:60]}'")
        more = hybrid_search(second_query, index, chunks, top_k=4)
        tool_log.append({"tool": "hybrid_search_secondary", "input": {"query": second_query}, "hits": len(more)})
        results = results + more

    # ── Step 3: number sources, generate, verify ──
    sources = number_sources(results)
    context, sources = build_context(sources)
    log.info(f"[AGENT] ✍️ Generating answer via Ollama ({settings.ollama_model}) from {len(sources)} sources...")
    answer = _generate_answer(question, context)
    tool_log.append({"tool": "ask_ollama", "input": {"question": question, "sources": len(sources)}})

    llm_ok = not answer.startswith("**Could not generate answer.**")
    check = {"cited": [], "invalid": []}
    if llm_ok:
        check = verify_citations(answer, len(sources))
        answer = strip_invalid(answer, check["invalid"])
        if not check["cited"]:
            answer += "\n\n> ⚠️ This answer carries no source citations — verify it against the sources below."

    top = answer_confidence(results)
    answer += f"\n\n---\n**Retrieval confidence:** {confidence_label(top)} ({top:.0%})"
    if check["cited"]:
        answer += " · **Cited sources:** " + ", ".join(f"[{n}]" for n in check["cited"])
    for s in sources:
        s["cited"] = s["n"] in check["cited"]

    log.info(f"[AGENT] ✅ Done ({len(tool_log)} steps, cited={check['cited']}, invalid={check['invalid']})")
    return {
        "answer": answer, "tool_calls": tool_log, "answerable": True, "question": question,
        "citations": sources, "citation_check": check,
    }


def answer_question(question: str, index=None, chunks: list = None, **kwargs) -> dict:
    """Compatibility wrapper."""
    return run_agent(question, index, chunks)

