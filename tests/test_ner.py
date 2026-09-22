import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch

from ner import ner_extractor as ner

TEXT = ("Northwind Analytics Ltd. agrees to pay USD 18,500 within 30 days. "
        "Maria Lopez shall deliver the report by 20 June 2025. Total fees are 4.2 million dollars.")


def _fake_pipeline(chunk):
    return [{"entity_group": "PER", "word": "Maria Lopez", "score": 0.99},
            {"entity_group": "ORG", "word": "Northwind Analytics Ltd", "score": 0.98},
            {"entity_group": "LOC", "word": "London", "score": 0.4}]      # below confidence cutoff


def test_extract_entities_end_to_end_with_mocked_bert():
    with patch.object(ner, "get_ner_pipeline", return_value=_fake_pipeline):
        r = ner.extract_entities(TEXT)
    assert r["PERSON"] == ["Maria Lopez"] and r["ORGANIZATION"] == ["Northwind Analytics Ltd"]
    assert r["LOCATION"] == []                                              # low-confidence entity dropped
    assert any("USD 18,500" in f for f in r["FINANCIAL_VALUES"])
    assert any("4.2 million" in f for f in r["FINANCIAL_VALUES"])
    assert any("shall deliver" in o for o in r["OBLIGATIONS"])


def test_financial_values_keep_their_magnitude_word():
    """Regression: 'USD 14.8 million' used to be truncated to 'USD 14.8', losing 6 orders of magnitude."""
    with patch.object(ner, "get_ner_pipeline", return_value=lambda chunk: []):
        r = ner.extract_entities("Revenue for the quarter was USD 14.8 million, up 9 percent year over year.")
    assert "USD 14.8 million" in r["FINANCIAL_VALUES"]
    assert "USD 14.8" not in r["FINANCIAL_VALUES"]


def test_empty_text_returns_empty_categories():
    assert all(v == [] for v in ner.extract_entities("  ").values())


def test_split_into_chunks_respects_limit():
    chunks = ner._split_into_chunks("One sentence here. " * 100, max_chars=100)
    assert len(chunks) > 1 and all(len(c) < 200 for c in chunks)
