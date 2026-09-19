import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.run_eval import evaluate
from rag.retriever import answer_confidence, is_query_answerable


def test_answer_confidence_prefers_vector_score_over_inflated_hybrid():
    hit = ("text", 0.75, {"vector_score": 0.1, "bm25_score": 1.0})  # unrelated query: BM25 max-normalised to 1.0
    assert answer_confidence([hit]) == 0.1
    assert not is_query_answerable([hit], threshold=0.3)


def test_answer_confidence_falls_back_to_hybrid_without_vectors():
    assert answer_confidence([("t", 0.4, {"vector_score": 0.0})]) == 0.4


def test_retrieval_quality_regression_bm25_only():
    """Model-free floor so CI can run it; run `python eval/run_eval.py` for the full hybrid numbers."""
    r = evaluate(use_vectors=False)
    assert r["retrieval"]["recall@5"] >= 0.9
    assert r["compliance_offline_accuracy"] >= 0.9
