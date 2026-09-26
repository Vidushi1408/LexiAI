"""
Sentence Embeddings — cached model singleton + disk cache for training data.
Fixes: slow startup caused by re-loading model and re-encoding on every run.
"""
import os
import hashlib
import numpy as np

# ── Model singleton ───────────────────────────────────────────────────────────
_model = None

import logging
log = logging.getLogger("lexi.embeddings.sentence_embeddings")


def _get_model():
    """Load SentenceTransformer once and reuse — avoids 3-5s reload on every call."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        # paraphrase-MiniLM-L3-v2 is ~3x faster than all-MiniLM-L6-v2
        # with only a small quality drop — fine for classification.
        # Change back to "all-MiniLM-L6-v2" if accuracy matters more.
        model_name = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
        log.info(f"[EMBED] Loading SentenceTransformer: {model_name}")
        _model = SentenceTransformer(model_name)
        log.info("[EMBED] Model ready.")
    return _model


# ── Disk cache helpers ────────────────────────────────────────────────────────
_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "models", "embed_cache")

def _cache_path(sentences: list[str]) -> str:
    """Return a .npy path uniquely identifying this list of sentences AND the model that would
    encode them — keying on text alone let a cache entry from an earlier EMBED_MODEL silently
    return wrong-dimension vectors for the same text under a different one."""
    os.makedirs(_CACHE_DIR, exist_ok=True)
    model_name = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
    key = hashlib.md5(f"{model_name}\n".encode() + "\n".join(sentences).encode()).hexdigest()
    return os.path.join(_CACHE_DIR, f"{key}.npy")


# ── Public API ────────────────────────────────────────────────────────────────
def embed_sentences(sentences: list[str], use_cache: bool = True) -> np.ndarray:
    """
    Encode sentences to 384-dim vectors.

    - First call for a given list: encodes + saves to disk (~30-60s for 360 samples).
    - Subsequent calls with same list: loads from disk in <0.5s.
    - use_cache=False forces re-encoding (e.g. after model change).
    """
    if not sentences:
        return np.array([])

    cache_file = _cache_path(sentences)

    if use_cache and os.path.exists(cache_file):
        log.info(f"[EMBED] ✅ Cache hit — loading {len(sentences)} embeddings from disk")
        return np.load(cache_file)

    log.info(f"[EMBED] Encoding {len(sentences)} sentences (first time, ~30-60s)...")
    model = _get_model()
    vecs  = model.encode(
        sentences,
        batch_size=64,           # process in chunks — avoids memory spikes
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    if use_cache:
        np.save(cache_file, vecs)
        log.info(f"[EMBED] 💾 Cached at {cache_file}")

    return vecs


def embed_query(query: str) -> np.ndarray:
    """Encode a single query string — always live, no caching."""
    model = _get_model()
    return model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]