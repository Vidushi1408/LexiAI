# rag/retriever.py

"""
Hybrid Search & Retrieval Engine — Lexi AI
-------------------------------------------
Combines BM25 keyword matching + FAISS dense vector search for high-precision
document retrieval.
"""

# pyrefly: ignore [missing-import]
import faiss
# pyrefly: ignore [missing-import]
import numpy as np
from embeddings.sentence_embeddings import embed_query as embed_single

try:
    # pyrefly: ignore [missing-import]
    from rank_bm25 import BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25_AVAILABLE = False


def hybrid_search(query: str, index, chunks: list, top_k: int = 5, alpha: float = 0.5) -> list:
    """
    Executes Hybrid Search combining BM25 keyword scores and FAISS Vector similarity.
    
    Args:
        query (str): Search query
        index: Loaded FAISS index
        chunks (list): Document text chunks
        top_k (int): Number of top results to return
        alpha (float): Weight for Vector vs BM25 (0.5 = equal blend)

    Returns:
        list of tuples: (chunk_text, final_hybrid_score, metadata_dict)
    """
    if not chunks:
        return []

    # 1. Vector Search
    vector_scores = {}
    if index is not None:
        query_vec = embed_single(query).astype(np.float32).reshape(1, -1)
        faiss.normalize_L2(query_vec)
        D, I = index.search(query_vec, min(len(chunks), top_k * 3))
        for score, idx in zip(D[0], I[0]):
            if idx != -1 and idx < len(chunks):
                vector_scores[idx] = max(0.0, float(score))

    # 2. BM25 / Keyword Search
    bm25_scores = {}
    tokens = [w.lower() for w in query.split() if len(w) > 2]
    
    raw_bm25 = []
    if _BM25_AVAILABLE and chunks:
        corpus = [c.lower().split() for c in chunks]
        raw_bm25 = BM25Okapi(corpus).get_scores(tokens)
    # BM25's IDF collapses to 0 on very small documents, so fall back to term overlap
    if len(raw_bm25) and max(raw_bm25) > 0:
        max_b = max(raw_bm25)
        for i, score in enumerate(raw_bm25):
            bm25_scores[i] = float(score) / max_b
    else:
        for i, chunk in enumerate(chunks):
            cl = chunk.lower()
            match_cnt = sum(1 for t in tokens if t in cl)
            bm25_scores[i] = min(1.0, match_cnt / max(1, len(tokens)))

    # 3. Hybrid Blending
    results = []
    for idx in range(len(chunks)):
        v_score = vector_scores.get(idx, 0.0)
        b_score = bm25_scores.get(idx, 0.0)
        final_score = round(alpha * v_score + (1 - alpha) * b_score, 4)

        if final_score > 0.05:
            # Matched keywords
            matched_words = [t for t in tokens if t in chunks[idx].lower()]
            page = getattr(chunks[idx], "page", None)
            meta = {
                "vector_score": round(v_score, 3),
                "bm25_score": round(b_score, 3),
                "doc_name": getattr(chunks[idx], "doc", "Primary Document"),
                "page": page if page is not None else "n/a",
                "location": getattr(chunks[idx], "label", "") or (f"Page {page}" if page else "location unknown"),
                "chunk_id": idx,
                "matched_keywords": list(set(matched_words)),
            }
            results.append((chunks[idx], final_score, meta))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def retrieve_relevant_chunks(query: str, index, chunks: list, top_k: int = 3) -> list:
    """
    Backwards-compatible API wrapper returning (chunk_text, similarity_score) tuples.
    Uses Hybrid Search under the hood.
    """
    hybrid = hybrid_search(query, index, chunks, top_k=top_k)
    return [(chunk, score) for chunk, score, _ in hybrid]


def build_context_string(retrieved_chunks: list, max_chars: int = 2000) -> str:
    """
    Combines retrieved chunks into a cited context string for LLM generation.
    """
    context_parts = []
    total_chars = 0

    for i, item in enumerate(retrieved_chunks):
        if isinstance(item, tuple) and len(item) == 3:
            chunk, score, meta = item
            labeled = f"[Citation {i+1} | Doc: {meta['doc_name']} | Location: {meta['location']} | Relevance: {score:.2f}]\n{chunk}"
        else:
            chunk, score = item
            labeled = f"[Citation {i+1} | Score: {score:.2f}]\n{chunk}"

        if total_chars + len(labeled) > max_chars:
            break

        context_parts.append(labeled)
        total_chars += len(labeled)

    return "\n\n".join(context_parts)


def answer_confidence(retrieved_chunks: list) -> float:
    """
    How well the best retrieved passage matches the query, on a 0-1 scale.
    Uses the raw vector (cosine) similarity: the hybrid score is unusable for gating because BM25
    is max-normalised, which gives the top chunk 1.0 on the keyword side even for unrelated queries.
    Falls back to the hybrid score when no vector scores exist (BM25-only mode).
    """
    if not retrieved_chunks:
        return 0.0
    vec = [it[2].get("vector_score", 0.0) for it in retrieved_chunks if len(it) == 3]
    if vec and max(vec) > 0:
        return float(max(vec))
    return float(retrieved_chunks[0][1])


def is_query_answerable(retrieved_chunks: list, threshold: float = 0.3) -> bool:
    """Checks if the best retrieved passage is relevant enough to answer from."""
    return answer_confidence(retrieved_chunks) >= threshold
