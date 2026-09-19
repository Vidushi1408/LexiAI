import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch

from rag import agent
from rag.citations import number_sources, build_context, verify_citations, strip_invalid, confidence_label


def _hit(text, score, chunk_id, doc="c.pdf", loc="Page 2"):
    return (text, score, {"doc_name": doc, "location": loc, "chunk_id": chunk_id})


def test_number_sources_dedupes_and_numbers():
    src = number_sources([_hit("a", .9, 1), _hit("a again", .8, 1), _hit("b", .7, 2)])
    assert [s["n"] for s in src] == [1, 2]
    assert src[0]["text"] == "a"


def test_build_context_respects_budget_but_keeps_first():
    src = number_sources([_hit("x" * 50, .9, 1), _hit("y" * 50, .8, 2)])
    ctx, used = build_context(src, max_chars=10)
    assert len(used) == 1 and ctx.startswith("[1] c.pdf — Page 2")


def test_verify_and_strip_invalid_markers():
    check = verify_citations("Notice is 90 days [2]. Fees apply [7].", n_sources=3)
    assert check == {"cited": [2], "invalid": [7]}
    assert strip_invalid("Fees apply [7].", [7]) == "Fees apply ."


def test_confidence_label():
    assert (confidence_label(.7), confidence_label(.4), confidence_label(.1)) == ("High", "Medium", "Low")


def _run(hits, llm_reply):
    with patch("rag.retriever.hybrid_search", return_value=hits), \
         patch.object(agent, "_call_ollama", return_value=llm_reply):
        return agent.run_agent("What is the notice period?", index=object(), chunks=["x"])


def test_agent_refuses_below_relevance_threshold():
    res = _run([_hit("weak", 0.05, 1)], "should not be called")
    assert not res["answerable"] and "Not found" in res["answer"]


def test_agent_marks_cited_sources_and_drops_fake_ones():
    res = _run([_hit("Ninety days notice.", .8, 1), _hit("Fees.", .5, 2)],
               "Notice is 90 days [1]. Something invented [9].")
    assert res["citation_check"] == {"cited": [1], "invalid": [9]}
    assert "[9]" not in res["answer"]
    assert [s["cited"] for s in res["citations"]] == [True, False]
    assert "Retrieval confidence: High" in res["answer"].replace("**", "")


def test_agent_warns_when_answer_has_no_citations():
    res = _run([_hit("Ninety days notice.", .8, 1)], "Notice is 90 days.")
    assert "no source citations" in res["answer"]


def test_agent_offline_llm_has_no_citation_warning():
    res = _run([_hit("Ninety days notice.", .8, 1)], None)
    assert "Could not generate answer" in res["answer"]
    assert "no source citations" not in res["answer"]
