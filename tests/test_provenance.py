import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz

from rag.indexer import _chunk_pages
from rag.retriever import hybrid_search, build_context_string
from utils.pdf_reader import load_uploaded_file_pages


class _Upload:
    def __init__(self, name, data): self.name, self._d = name, data
    def read(self): return self._d


def _two_page_pdf() -> bytes:
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Payment is due within thirty days of the invoice date. Late fees apply.")
    doc.new_page().insert_text((72, 72), "Either party may terminate with ninety days written notice. Termination takes effect at month end.")
    data = doc.tobytes()
    doc.close()
    return data


def test_pdf_pages_keep_real_page_numbers():
    pages = load_uploaded_file_pages(_Upload("contract.pdf", _two_page_pdf()))
    assert [p["page"] for p in pages] == [1, 2]
    assert "Termination" in pages[1]["text"]


def test_retrieved_chunk_reports_true_page_and_doc():
    pages = [{**p, "doc": "contract.pdf"} for p in load_uploaded_file_pages(_Upload("contract.pdf", _two_page_pdf()))]
    chunks = _chunk_pages(pages)
    results = hybrid_search("termination notice", None, chunks, top_k=1)  # BM25 path (no vector index)
    chunk, score, meta = results[0]
    assert meta["doc_name"] == "contract.pdf"
    assert meta["page"] == 2
    assert "Page 2" in meta["location"]
    assert "contract.pdf | Location: Page 2" in build_context_string(results)


def test_plain_text_falls_back_to_single_location():
    pages = load_uploaded_file_pages(_Upload("notes.txt", b"Action: send the report by Friday. Owner is Priya."))
    assert pages[0]["label"] == "Full document"
