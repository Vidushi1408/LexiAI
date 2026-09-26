# tests/test_embedding_cache.py
"""Both the per-sentence embedding cache (embeddings/sentence_embeddings.py) and the FAISS index
cache (rag/indexer.py) key on disk by content only — this must also include which embedding model
produced the vectors, or a cache entry from an earlier EMBED_MODEL silently returns wrong-dimension
vectors for the same text under a different one, crashing FAISS's index.search() at query time
(see db.py's neighbouring migration-safety-net tests for the same "don't trust the past" spirit)."""
import os
from unittest.mock import patch

import numpy as np

import embeddings.sentence_embeddings as se
import rag.indexer as indexer


def test_embed_sentences_cache_key_includes_model_name(monkeypatch):
    sentences = ["A distinctive test sentence for cache-key isolation."]

    monkeypatch.setenv("EMBED_MODEL", "model-a")
    path_a = se._cache_path(sentences)
    monkeypatch.setenv("EMBED_MODEL", "model-b")
    path_b = se._cache_path(sentences)

    assert path_a != path_b


def test_embed_sentences_does_not_reuse_a_cache_entry_from_a_different_model(monkeypatch):
    sentences = ["Another distinctive sentence, unlikely to collide with real cache entries."]
    written = []

    def fake_model(dim):
        class _Model:
            def encode(self, sents, **kw):
                return np.ones((len(sents), dim), dtype=np.float32)
        return _Model()

    try:
        monkeypatch.setenv("EMBED_MODEL", "fake-model-8dim")
        with patch("embeddings.sentence_embeddings._get_model", return_value=fake_model(8)):
            v1 = se.embed_sentences(sentences, use_cache=True)
        written.append(se._cache_path(sentences))
        assert v1.shape[1] == 8

        monkeypatch.setenv("EMBED_MODEL", "fake-model-16dim")
        with patch("embeddings.sentence_embeddings._get_model", return_value=fake_model(16)):
            v2 = se.embed_sentences(sentences, use_cache=True)
        written.append(se._cache_path(sentences))
        assert v2.shape[1] == 16   # not the stale 8-dim vector cached under the other model's key
    finally:
        for p in written:
            if os.path.exists(p):
                os.remove(p)


def test_index_document_cache_key_includes_model_name(monkeypatch):
    text = "A distinctive contract clause used only by this cache-key isolation test."
    written = [indexer._INDEX_FILE, indexer._CHUNKS_FILE, indexer._HASH_FILE]

    def fake_embed(chunks, use_cache=True):
        dim = 8 if os.environ["EMBED_MODEL"] == "fake-model-8dim" else 16
        return np.ones((len(chunks), dim), dtype=np.float32)

    try:
        monkeypatch.setenv("EMBED_MODEL", "fake-model-8dim")
        with patch("embeddings.sentence_embeddings.embed_sentences", side_effect=fake_embed):
            idx1, _ = indexer.index_document(text, save=True, force=True)
        assert idx1.d == 8

        # force=False: would happily load the cached 8-dim index if the cache key ignored the
        # model change — must rebuild instead, since a different model is now in use.
        monkeypatch.setenv("EMBED_MODEL", "fake-model-16dim")
        with patch("embeddings.sentence_embeddings.embed_sentences", side_effect=fake_embed):
            idx2, _ = indexer.index_document(text, save=True, force=False)
        assert idx2.d == 16
    finally:
        for p in written:
            if os.path.exists(p):
                os.remove(p)
