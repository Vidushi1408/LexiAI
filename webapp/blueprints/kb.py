# webapp/blueprints/kb.py
"""Knowledge Base & Upload: ingest documents, validate/scan them, and build the retrieval index."""
import logging
import os

from flask import Blueprint, flash, redirect, render_template, request, url_for

from rag.injection import scan as scan_injection
from utils.pdf_reader import load_uploaded_file_pages
from utils.upload_guard import safe_filename, validate_upload
from webapp.security import audit_event, login_required, analyst_required
from webapp.state import get_state
from webapp.uploads import FlaskUpload

log = logging.getLogger("lexi.web.kb")
bp = Blueprint("kb", __name__, url_prefix="/knowledge-base")

# Extensions where utils.pdf_reader can't extract real per-page/per-row provenance, so citations
# for these files will show "Full document" instead of a page number. Only .csv is called out —
# .txt/.md/.eml never had page structure to begin with, so "Full document" there isn't a loss of
# anything; a CSV, by contrast, often encodes distinct rows/records the app can't see individually.
FLAT_INGESTION_EXTENSIONS = {".csv"}


@bp.route("/")
@login_required
def index():
    state = get_state()
    preview = None
    if state.raw_text:
        preview = state.raw_text[:3000] + ("..." if len(state.raw_text) > 3000 else "")
    return render_template("kb.html", state=state, preview=preview)


@bp.route("/upload", methods=["POST"])
@analyst_required
def upload():
    state = get_state()
    files = [f for f in request.files.getlist("documents") if f and f.filename]
    if not files:
        flash("Choose at least one file to upload.", "error")
        return redirect(url_for("kb.index"))

    combined_text, loaded, failed, all_pages, flagged, flat = "", [], [], [], {}, []
    for storage in files:
        up = FlaskUpload(storage)
        safe = safe_filename(up.name)
        ok, reason = validate_upload(up.name, up.getvalue())
        if not ok:
            failed.append(f"{safe} — {reason}")
            audit_event("upload_rejected", document=safe, reason=reason)
            continue
        pages = load_uploaded_file_pages(up)
        text = "\n\n".join(p["text"] for p in pages)
        if text and len(text.strip()) > 30:
            combined_text += f"\n\n=== {safe} ===\n\n{text}"
            loaded.append(safe)
            all_pages.extend({**p, "doc": safe} for p in pages)
            if os.path.splitext(safe)[1].lower() in FLAT_INGESTION_EXTENSIONS:
                flat.append(safe)
            if hits := scan_injection(text):
                flagged[safe] = hits
        else:
            failed.append(f"{safe} — no readable text")

    if combined_text.strip():
        state.clear_documents()
        state.raw_text = combined_text.strip()
        state.file_name = "_".join(sorted(loaded))
        state.pages = all_pages
        state.flat_ingestion = flat
        audit_event("documents_uploaded", documents=loaded, failed=failed, pages=len(all_pages), flat=flat)
        for name in loaded:
            flash(f"✅ {name}", "success")
    for name in failed:
        flash(f"❌ {name}", "error")
    for name, hits in flagged.items():
        flash(f"⚠️ {name} contains text that looks like instructions to an AI ({', '.join(hits)}). "
              "It will be treated as data only — review the document before relying on results.", "warning")
        audit_event("injection_suspected", document=name, patterns=hits)
    if flat:
        flash(f"ℹ️ {', '.join(flat)} — CSV files are ingested as a single block of text, so citations "
              "for them will show \"Full document\" instead of a row or page number.", "info")
    if not combined_text.strip() and not failed:
        flash("Unsupported or unreadable files.", "error")
    return redirect(url_for("kb.index"))


@bp.route("/zero-retention", methods=["POST"])
@analyst_required
def set_zero_retention():
    state = get_state()
    state.zero_retention = request.form.get("zero_retention") == "on"
    return redirect(url_for("kb.index"))


@bp.route("/process", methods=["POST"])
@analyst_required
def process():
    state = get_state()
    if not state.raw_text:
        flash("Upload documents first.", "error")
        return redirect(url_for("kb.index"))

    from preprocessing.pipeline import run_preprocessing_pipeline
    from rag.indexer import index_document

    result = run_preprocessing_pipeline(state.raw_text)
    state.pipeline_result = result

    idx, chunks = index_document(state.raw_text, chunk_size=3, overlap=1, save=True,
                                  pages=state.pages, persist=not state.zero_retention)
    state.faiss_index = idx
    state.chunks = chunks
    state.processed = True
    audit_event("knowledge_base_processed", chunks=len(chunks), zero_retention=state.zero_retention)
    flash("Knowledge base processed successfully.", "success")
    return redirect(url_for("kb.index"))


@bp.route("/clear", methods=["POST"])
@analyst_required
def clear():
    get_state().clear_documents()
    audit_event("session_cleared")
    flash("Knowledge base cleared.", "info")
    return redirect(url_for("kb.index"))
