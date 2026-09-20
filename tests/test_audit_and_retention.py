import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch

import numpy as np

from audit import log as audit
from rag import indexer


def test_chain_verifies_and_records_metadata(tmp_path):
    p = str(tmp_path / "a.jsonl")
    audit.record("documents_uploaded", user="priya", path=p, documents=["a.pdf"])
    audit.record("question_asked", user="priya", path=p, query=audit.fingerprint("secret question"))
    assert audit.verify(p) == (True, "Audit log intact (2 entries).")
    assert "secret question" not in open(p).read()
    assert audit.read(p)[1]["prev_hash"] == audit.read(p)[0]["hash"]


def test_tampering_is_detected(tmp_path):
    p = str(tmp_path / "a.jsonl")
    for i in range(3):
        audit.record("x", path=p, i=i)
    lines = open(p).read().splitlines()
    entry = json.loads(lines[1]); entry["user"] = "someone_else"
    lines[1] = json.dumps(entry)
    open(p, "w").write("\n".join(lines) + "\n")
    ok, msg = audit.verify(p)
    assert not ok and "#2" in msg


def test_deleting_an_entry_is_detected(tmp_path):
    p = str(tmp_path / "a.jsonl")
    for i in range(3):
        audit.record("x", path=p, i=i)
    lines = open(p).read().splitlines()
    open(p, "w").write("\n".join([lines[0], lines[2]]) + "\n")
    assert not audit.verify(p)[0]


def test_csv_export_has_all_rows(tmp_path):
    p = str(tmp_path / "a.jsonl")
    audit.record("a", path=p); audit.record("b", path=p)
    assert len(audit.export_csv(p).strip().splitlines()) == 3   # header + 2


def _fake_embed(chunks, use_cache=True):
    rng = np.random.default_rng(0)
    v = rng.random((len(chunks), 8)).astype(np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def test_zero_retention_writes_nothing_to_disk(tmp_path):
    idx_dir = tmp_path / "saved_index"
    with patch.object(indexer, "_INDEX_DIR", str(idx_dir)), \
         patch.object(indexer, "_INDEX_FILE", str(idx_dir / "faiss.index")), \
         patch.object(indexer, "_CHUNKS_FILE", str(idx_dir / "chunks.pkl")), \
         patch.object(indexer, "_HASH_FILE", str(idx_dir / "text_hash.txt")), \
         patch("embeddings.sentence_embeddings.embed_sentences", side_effect=_fake_embed) as emb:
        index, chunks = indexer.index_document("First clause. Second clause. Third clause. Fourth clause.",
                                               persist=False)
    assert index.ntotal == len(chunks) > 0
    assert not idx_dir.exists()                          # nothing saved
    assert emb.call_args.kwargs["use_cache"] is False    # embedding cache disabled too


def test_normal_mode_still_persists(tmp_path):
    idx_dir = tmp_path / "saved_index"
    with patch.object(indexer, "_INDEX_DIR", str(idx_dir)), \
         patch.object(indexer, "_INDEX_FILE", str(idx_dir / "faiss.index")), \
         patch.object(indexer, "_CHUNKS_FILE", str(idx_dir / "chunks.pkl")), \
         patch.object(indexer, "_HASH_FILE", str(idx_dir / "text_hash.txt")), \
         patch("embeddings.sentence_embeddings.embed_sentences", side_effect=_fake_embed):
        indexer.index_document("First clause. Second clause. Third clause. Fourth clause.")
    assert (idx_dir / "faiss.index").exists()
