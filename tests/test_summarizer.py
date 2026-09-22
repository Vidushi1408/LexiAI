import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch

from generative import summarizer
from rag.indexer import Chunk


def _chunk(text, doc, page):
    c = Chunk(text)
    c.doc, c.page, c.label = doc, page, f"Page {page}"
    return c


CHUNKS = [
    _chunk("The loan facility is USD 2,500,000 over five years.", "loan.pdf", 1),
    _chunk("Interest is fixed at 7.25 percent per annum.", "loan.pdf", 2),
    _chunk("Revenue for Q3 was USD 14.8 million.", "report.pdf", 1),
]


def test_briefing_with_chunks_cites_real_sources_not_a_fabricated_score():
    with patch.object(summarizer, "_call_ollama",
                      return_value="## Bottom Line\nThe loan is USD 2,500,000 [1] at 7.25 percent [2]."):
        result = summarizer.summarize_text("placeholder raw text long enough to pass the length check.",
                                           style="concise", chunks=CHUNKS)
    assert "Confidence Score" not in result          # the old self-reported line is gone
    assert "Cited sources:** [1], [2]" in result
    assert "Documents referenced:** 1 of 2" in result
    assert "loan.pdf" in result
    assert "Not covered in this briefing: report.pdf" in result


def test_briefing_strips_invented_citation_numbers():
    with patch.object(summarizer, "_call_ollama", return_value="The deal closed [1] under new terms [9]."):
        result = summarizer.summarize_text("placeholder raw text long enough to pass the length check.",
                                           style="concise", chunks=CHUNKS)
    assert "[9]" not in result
    assert "[1]" in result


def test_briefing_with_no_citations_warns_instead_of_fabricating_confidence():
    with patch.object(summarizer, "_call_ollama", return_value="The deal closed under new terms."):
        result = summarizer.summarize_text("placeholder raw text long enough to pass the length check.",
                                           style="concise", chunks=CHUNKS)
    assert "carries no source citations" in result
    assert "Confidence Score" not in result


def test_briefing_falls_back_to_extractive_when_llm_offline():
    with patch.object(summarizer, "_call_ollama", return_value=None):
        result = summarizer.summarize_text("placeholder raw text long enough to pass the length check.",
                                           style="concise", chunks=CHUNKS)
    assert "System Note" in result and "88%" not in result   # the old fabricated fallback number is gone


def test_legacy_raw_text_path_still_works_without_chunks():
    with patch.object(summarizer, "_call_ollama", return_value="A plain uncited summary."):
        result = summarizer.summarize_text("Some raw document text that is comfortably long enough to pass "
                                           "the minimum-length check.", style="concise")
    assert result == "A plain uncited summary."
