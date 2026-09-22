# eval/run_eval.py
"""
Lexi AI evaluation harness.

Measures, on a labelled sector dataset in eval/datasets/*.json:
  * retrieval  — recall@k and MRR: does the gold passage (right doc + page + text) appear in the top-k?
  * refusal    — with the relevance threshold, do we answer answerable questions and refuse the rest?
                 (also sweeps thresholds so the best value can be chosen from data)
  * compliance — offline rule-based scan status accuracy against labelled expectations

Usage:
    python eval/run_eval.py                          # full: embeddings + FAISS + BM25, all sectors
    python eval/run_eval.py --dataset finance         # a single sector (name in eval/datasets/, or a path)
    python eval/run_eval.py --no-vectors              # BM25 only (no model download needed)
    python eval/run_eval.py --min-recall5 0.8         # exit 1 if any sector's recall@5 is below this (CI gate)
    python eval/run_eval.py --json                    # machine-readable output
"""
import argparse, glob, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from generative.quiz_generator import _rule_based_compliance_fallback
from generative.quote_check import _norm
from rag.indexer import _chunk_pages
from rag.retriever import hybrid_search, answer_confidence

DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")
KS = (1, 3, 5)


def list_sectors() -> list[str]:
    return sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(DATASET_DIR, "*.json")))


def resolve_dataset_path(name: str) -> str:
    """Accepts a sector name (e.g. "finance"), a filename, or a full path."""
    if os.path.exists(name):
        return name
    candidate = os.path.join(DATASET_DIR, f"{name}.json")
    if os.path.exists(candidate):
        return candidate
    raise FileNotFoundError(f"No dataset named '{name}'. Available: {', '.join(list_sectors())}")


def build_index(chunks, use_vectors: bool):
    if not use_vectors:
        return None
    import faiss, numpy as np
    from embeddings.sentence_embeddings import embed_sentences
    vecs = embed_sentences([str(c) for c in chunks], use_cache=True).astype(np.float32)
    index = faiss.IndexFlatIP(vecs.shape[1])
    index.add(vecs)
    return index


def is_gold(chunk, meta, q) -> bool:
    return (meta["doc_name"] == q["doc"] and meta["page"] == q["page"]
            and _norm(q["must_contain"]) in _norm(str(chunk)))


def evaluate(dataset: str = "legal", use_vectors: bool = True, threshold: float | None = None) -> dict:
    path = resolve_dataset_path(dataset)
    data = json.load(open(path))
    pages = [{**p, "doc": d["name"]} for d in data["documents"] for p in d["pages"]]
    chunks = _chunk_pages(pages)
    index = build_index(chunks, use_vectors)
    threshold = settings.min_relevance if threshold is None else threshold

    answerable = [q for q in data["questions"] if q["answerable"]]
    unanswerable = [q for q in data["questions"] if not q["answerable"]]

    # ── retrieval ──
    hits = {k: 0 for k in KS}
    rr, failures, top_scores_ans = 0.0, [], []
    for q in answerable:
        res = hybrid_search(q["q"], index, chunks, top_k=max(KS))
        top_scores_ans.append(answer_confidence(res))
        rank = next((i for i, (c, _, m) in enumerate(res, 1) if is_gold(c, m, q)), None)
        for k in KS:
            hits[k] += bool(rank and rank <= k)
        rr += 1 / rank if rank else 0.0
        if not rank or rank > 3:
            failures.append({"q": q["q"], "rank": rank})
    n = len(answerable)

    # ── refusal / threshold sweep ──
    top_scores_un = []
    for q in unanswerable:
        top_scores_un.append(answer_confidence(hybrid_search(q["q"], index, chunks, top_k=max(KS))))

    def refusal_at(t):
        answered = sum(s >= t for s in top_scores_ans) / n
        refused = sum(s < t for s in top_scores_un) / len(unanswerable)
        return {"threshold": t, "answered_ok": round(float(answered), 3), "refused_ok": round(float(refused), 3),
                "balanced": round(float((answered + refused) / 2), 3)}

    sweep = [refusal_at(round(t / 100, 2)) for t in range(5, 71, 5)]

    # ── compliance (offline rule scan) ──
    correct = total = 0
    for case in data.get("compliance", []):
        sents = [s.strip() + "." for p in pages if p["doc"] == case["doc"] for s in p["text"].split(".") if s.strip()]
        got = {r["requirement"]: r["status"] for r in _rule_based_compliance_fallback(sents)}
        for req, expected in case["expect"].items():
            total += 1
            correct += got.get(req) == expected

    return {
        "dataset": os.path.splitext(os.path.basename(path))[0],
        "mode": "hybrid (BM25 + vectors)" if use_vectors else "BM25 only",
        "questions": {"answerable": n, "unanswerable": len(unanswerable)},
        "retrieval": {**{f"recall@{k}": round(hits[k] / n, 3) for k in KS}, "mrr": round(rr / n, 3)},
        "refusal": {"configured": refusal_at(threshold), "best_balanced": max(sweep, key=lambda r: r["balanced"]),
                    "sweep": sweep},
        "compliance_offline_accuracy": round(correct / total, 3) if total else None,
        "retrieval_failures": failures,
    }


def _print(r: dict) -> None:
    print(f"\n[{r['dataset']}] Lexi AI evaluation — {r['mode']}  "
          f"({r['questions']['answerable']} answerable / {r['questions']['unanswerable']} unanswerable)")
    print("Retrieval :", "  ".join(f"{k}={v}" for k, v in r["retrieval"].items()))
    c, b = r["refusal"]["configured"], r["refusal"]["best_balanced"]
    print(f"Refusal   : threshold {c['threshold']} -> answered_ok={c['answered_ok']} refused_ok={c['refused_ok']}")
    print(f"            best threshold {b['threshold']} -> answered_ok={b['answered_ok']} refused_ok={b['refused_ok']}")
    if r["compliance_offline_accuracy"] is not None:
        print("Compliance (offline keyword scan) accuracy:", r["compliance_offline_accuracy"])
    for f in r["retrieval_failures"]:
        print("  miss:", f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=None, help="sector name (see eval/datasets/), or 'all' (default)")
    ap.add_argument("--no-vectors", action="store_true")
    ap.add_argument("--min-recall5", type=float, default=None, help="exit 1 if any sector's recall@5 is below this")
    ap.add_argument("--json", action="store_true", help="print raw JSON only")
    a = ap.parse_args()

    sectors = list_sectors() if a.dataset in (None, "all") else [a.dataset]
    results = [evaluate(dataset=s, use_vectors=not a.no_vectors) for s in sectors]

    if a.json:
        print(json.dumps(results if len(results) > 1 else results[0], indent=2))
    else:
        for r in results:
            _print(r)
        if len(results) > 1:
            print(f"\nOverall recall@5 across {len(results)} sectors:",
                  round(sum(r["retrieval"]["recall@5"] for r in results) / len(results), 3))

    worst = min(r["retrieval"]["recall@5"] for r in results)
    if a.min_recall5 is not None and worst < a.min_recall5:
        print(f"FAIL: worst sector recall@5 {worst} < {a.min_recall5}")
        sys.exit(1)


if __name__ == "__main__":
    main()
