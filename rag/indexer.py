"""
RAG Indexer — FAISS with disk persistence.
Fixes: rebuilding the vector index from scratch on every app startup.
"""
import os
import hashlib
import pickle
import numpy as np

_INDEX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "rag", "saved_index")

_INDEX_FILE  = os.path.join(_INDEX_DIR, "faiss.index")
_CHUNKS_FILE = os.path.join(_INDEX_DIR, "chunks.pkl")
_HASH_FILE   = os.path.join(_INDEX_DIR, "text_hash.txt")


class Chunk(str):
    """A text chunk that remembers where it came from (a plain str everywhere else)."""
    doc:   str        = "Primary Document"
    page:  int | None = None
    label: str        = ""


def _text_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _chunk_text(text: str, chunk_size: int = 3, overlap: int = 1) -> list[str]:
    """Split text into overlapping sentence-window chunks."""
    import nltk
    try:
        sentences = nltk.sent_tokenize(text)
    except Exception:
        sentences = [s.strip() for s in text.split(".") if s.strip()]

    chunks, i = [], 0
    while i < len(sentences):
        chunk = " ".join(sentences[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk.strip())
        i += chunk_size - overlap

    return chunks


def _chunk_pages(pages: list[dict], chunk_size: int = 3, overlap: int = 1) -> list[Chunk]:
    """Chunk each page separately so every chunk keeps its true document and page."""
    chunks = []
    for p in pages:
        for text in _chunk_text(p["text"], chunk_size=chunk_size, overlap=overlap):
            c = Chunk(text)
            c.doc, c.page, c.label = p.get("doc", "Primary Document"), p.get("page"), p.get("label", "")
            chunks.append(c)
    return chunks


def index_document(
    text: str,
    chunk_size: int = 3,
    overlap: int = 1,
    save: bool = True,
    force: bool = False,
    pages: list[dict] | None = None,
    persist: bool = True,
):
    """
    Build (or load from cache) a FAISS index for the given text.

    Returns
    -------
    index  : faiss.IndexFlatIP  (inner-product = cosine on normalized vecs)
    chunks : list[str]  (Chunk objects carry .doc / .page / .label when `pages` is given)
    """
    import faiss
    from embeddings.sentence_embeddings import embed_sentences

    if not persist:                 # zero-retention: never read or write anything on disk
        save = False
        force = True
    else:
        os.makedirs(_INDEX_DIR, exist_ok=True)
    current_hash = _text_hash(text + "".join(f"|{p.get('doc')}:{p.get('page')}" for p in pages or []))

    # ── Cache hit ──────────────────────────────────────────────────────────────
    if (
        not force
        and os.path.exists(_INDEX_FILE)
        and os.path.exists(_CHUNKS_FILE)
        and os.path.exists(_HASH_FILE)
    ):
        with open(_HASH_FILE) as f:
            saved_hash = f.read().strip()

        if saved_hash == current_hash:
            print("[INDEX] ✅ Cache hit — loading FAISS index from disk")
            index = faiss.read_index(_INDEX_FILE)
            with open(_CHUNKS_FILE, "rb") as f:
                chunks = pickle.load(f)
            print(f"[INDEX] Loaded {index.ntotal} vectors, {len(chunks)} chunks")
            return index, chunks

    # ── Build fresh ────────────────────────────────────────────────────────────
    print("[INDEX] Building FAISS index (document changed or first run)...")
    chunks = (_chunk_pages(pages, chunk_size, overlap) if pages
              else _chunk_text(text, chunk_size=chunk_size, overlap=overlap))
    print(f"[INDEX] {len(chunks)} chunks created")

    vecs = embed_sentences(chunks, use_cache=persist)    # safe — cache key is hash of sentences
    vecs = vecs.astype(np.float32)

    dim   = vecs.shape[1]
    index = faiss.IndexFlatIP(dim)   # cosine similarity (vecs are L2-normalized)
    index.add(vecs)

    if save:
        faiss.write_index(index, _INDEX_FILE)
        with open(_CHUNKS_FILE, "wb") as f:
            pickle.dump(chunks, f)
        with open(_HASH_FILE, "w") as f:
            f.write(current_hash)
        print(f"[INDEX] 💾 Saved to {_INDEX_DIR}")

    print(f"[INDEX] ✅ {index.ntotal} vectors indexed")
    return index, chunks


def load_index():
    """Load a previously saved index, or return (None, []) if not found."""
    import faiss

    if os.path.exists(_INDEX_FILE) and os.path.exists(_CHUNKS_FILE):
        try:
            index = faiss.read_index(_INDEX_FILE)
            with open(_CHUNKS_FILE, "rb") as f:
                chunks = pickle.load(f)
            print(f"[INDEX] Loaded saved index ({index.ntotal} vectors)")
            return index, chunks
        except Exception as e:
            print(f"[INDEX] Failed to load index: {e}")
    return None, []