import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from eval.run_eval import evaluate, list_sectors, resolve_dataset_path
from rag.retriever import answer_confidence, is_query_answerable


def test_answer_confidence_prefers_vector_score_over_inflated_hybrid():
    hit = ("text", 0.75, {"vector_score": 0.1, "bm25_score": 1.0})  # unrelated query: BM25 max-normalised to 1.0
    assert answer_confidence([hit]) == 0.1
    assert not is_query_answerable([hit], threshold=0.3)


def test_answer_confidence_falls_back_to_hybrid_without_vectors():
    assert answer_confidence([("t", 0.4, {"vector_score": 0.0})]) == 0.4


def test_retrieval_quality_regression_bm25_only():
    """Model-free floor so CI can run it; run `python eval/run_eval.py` for the full hybrid numbers."""
    r = evaluate(dataset="legal", use_vectors=False)
    assert r["retrieval"]["recall@5"] >= 0.9
    assert r["compliance_offline_accuracy"] >= 0.9


def test_all_five_sector_datasets_are_registered():
    assert set(list_sectors()) == {"legal", "finance", "healthcare", "consulting", "hr_ops"}


def test_unknown_sector_name_raises_with_available_list():
    with pytest.raises(FileNotFoundError, match="finance"):
        resolve_dataset_path("not_a_real_sector")


@pytest.mark.parametrize("sector", ["legal", "finance", "healthcare", "consulting", "hr_ops"])
def test_every_sector_meets_a_retrieval_and_compliance_floor_bm25_only(sector):
    """Same model-free floor as legal, applied per sector so a bad dataset/regression is caught early."""
    r = evaluate(dataset=sector, use_vectors=False)
    assert r["retrieval"]["recall@5"] >= 0.85, r["retrieval_failures"]
    if r["compliance_offline_accuracy"] is not None:
        assert r["compliance_offline_accuracy"] >= 0.85
