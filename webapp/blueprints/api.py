# webapp/blueprints/api.py
"""
JSON API — /api/v1/*, for scripts and external callers rather than the browser UI.

Auth: either the normal browser session cookie, or an API key sent as
`Authorization: Bearer <key>` (generate one in Settings). A key-authenticated caller has no
cookie jar, so it gets one stable knowledge base per account instead of per browser tab — see
webapp/state.py's _current_sid(). That means: build up a knowledge base by calling /ingest and
/process with the SAME key, then /ask, /compliance etc. read from it, exactly like the browser UI.

This reuses the exact same business logic as the HTML pages (rag/, generative/, ner/) — no
separate code path to keep in sync, and the same role rules apply (analyst/admin to
ingest/process/analyse, any signed-in role to /ask and /search).
"""
import logging

from flask import Blueprint, jsonify, request

from audit import log as audit
from config import settings
from rag.injection import scan as scan_injection
from utils.pdf_reader import load_uploaded_file_pages
from utils.upload_guard import safe_filename, validate_upload
from webapp.security import api_analyst_required, api_login_required, audit_event, current_user
from webapp.state import get_state
from webapp.uploads import FlaskUpload

log = logging.getLogger("lexi.web.api")
bp = Blueprint("api", __name__, url_prefix="/api/v1")


def _require_processed(state):
    if not state.processed:
        return jsonify(error="not_processed", message="Ingest and process documents first."), 409
    return None


@bp.get("/status")
@api_login_required
def status():
    state = get_state()
    return jsonify(file_name=state.file_name, processed=state.processed, chunks=len(state.chunks),
                   zero_retention=state.zero_retention,
                   words=(state.pipeline_result or {}).get("word_count", 0))


@bp.post("/ingest")
@api_analyst_required
def ingest():
    state = get_state()
    files = [f for f in request.files.getlist("documents") if f and f.filename]
    if not files:
        return jsonify(error="no_files", message="Attach one or more files as 'documents'."), 400

    combined_text, loaded, failed, all_pages, flagged = "", [], [], [], {}
    for storage in files:
        up = FlaskUpload(storage)
        safe = safe_filename(up.name)
        ok, reason = validate_upload(up.name, up.getvalue())
        if not ok:
            failed.append({"file": safe, "reason": reason})
            audit_event("upload_rejected", document=safe, reason=reason)
            continue
        pages = load_uploaded_file_pages(up)
        text = "\n\n".join(p["text"] for p in pages)
        if text and len(text.strip()) > 30:
            combined_text += f"\n\n=== {safe} ===\n\n{text}"
            loaded.append(safe)
            all_pages.extend({**p, "doc": safe} for p in pages)
            if hits := scan_injection(text):
                flagged[safe] = hits
        else:
            failed.append({"file": safe, "reason": "no readable text"})

    if combined_text.strip():
        state.clear_documents()
        state.raw_text = combined_text.strip()
        state.file_name = "_".join(sorted(loaded))
        state.pages = all_pages
        audit_event("documents_uploaded", documents=loaded, failed=[f["file"] for f in failed],
                    pages=len(all_pages), via="api")
        for name, hits in flagged.items():
            audit_event("injection_suspected", document=name, patterns=hits)

    return jsonify(loaded=loaded, failed=failed, flagged=flagged), (200 if loaded else 422)


@bp.post("/process")
@api_analyst_required
def process():
    state = get_state()
    if not state.raw_text:
        return jsonify(error="nothing_to_process", message="Call /ingest first."), 409

    from generative.explainer import set_notes_context
    from preprocessing.pipeline import run_preprocessing_pipeline
    from rag.indexer import index_document

    result = run_preprocessing_pipeline(state.raw_text)
    state.pipeline_result = result
    set_notes_context(result["sentences"])

    idx, chunks = index_document(state.raw_text, chunk_size=3, overlap=1, save=True,
                                  pages=state.pages, persist=not state.zero_retention)
    state.faiss_index = idx
    state.chunks = chunks
    state.processed = True
    audit_event("knowledge_base_processed", chunks=len(chunks), zero_retention=state.zero_retention, via="api")
    return jsonify(processed=True, chunks=len(chunks))


@bp.post("/ask")
@api_login_required
def ask():
    state = get_state()
    if (err := _require_processed(state)) is not None:
        return err
    question = (request.get_json(silent=True) or request.form).get("question", "").strip()
    if not question:
        return jsonify(error="missing_question", message="Provide 'question' (JSON body or form field)."), 400

    from rag.agent import run_agent
    result = run_agent(question, state.faiss_index, state.chunks)
    if state.last_audited_question != question:
        state.last_audited_question = question
        audit_event("question_asked",
                    query=question if settings.audit_log_queries else audit.fingerprint(question),
                    answerable=result["answerable"], via="api",
                    sources=[{"doc": c["doc"], "location": c["location"], "cited": c.get("cited", False)}
                             for c in result.get("citations", [])])
    return jsonify(answer=result["answer"], answerable=result["answerable"],
                   confidence=result.get("confidence", 0.0), citations=result.get("citations", []))


@bp.post("/briefings")
@api_analyst_required
def briefing():
    state = get_state()
    if (err := _require_processed(state)) is not None:
        return err
    style = (request.get_json(silent=True) or request.form).get("style", "concise")

    from generative.summarizer import summarize_text
    state.summary_result = summarize_text(state.raw_text, style=style, chunks=state.chunks)
    audit_event("executive_briefing", style=style, via="api")
    return jsonify(briefing=state.summary_result)


@bp.post("/compliance")
@api_analyst_required
def compliance():
    state = get_state()
    if (err := _require_processed(state)) is not None:
        return err
    custom_rules = (request.get_json(silent=True) or request.form).get("custom_rules", "")

    from generative.quiz_generator import evaluate_compliance
    sents = (state.pipeline_result or {}).get("sentences", state.raw_text.split("."))
    state.compliance_result = evaluate_compliance(sents, custom_checklist=custom_rules)
    audit_event("compliance_check", custom_checklist=bool(custom_rules.strip()), via="api",
                results={s: sum(i["status"] == s for i in state.compliance_result) for s in ("PASS", "FAIL", "REVIEW")})
    return jsonify(results=state.compliance_result)


@bp.post("/entities")
@api_analyst_required
def entities():
    state = get_state()
    if (err := _require_processed(state)) is not None:
        return err
    from ner.ner_extractor import extract_entities
    state.entities_result = extract_entities(state.raw_text)
    audit_event("entity_extraction", via="api")
    return jsonify(entities=state.entities_result)


@bp.post("/actions")
@api_analyst_required
def actions():
    state = get_state()
    if (err := _require_processed(state)) is not None:
        return err
    from generative.action_item_extractor import extract_action_items
    state.action_items_result = extract_action_items(state.raw_text)
    audit_event("action_items", count=len(state.action_items_result), via="api")
    return jsonify(actions=state.action_items_result)


@bp.post("/search")
@api_login_required
def search():
    state = get_state()
    if (err := _require_processed(state)) is not None:
        return err
    query = (request.get_json(silent=True) or request.form).get("query", "").strip()
    if not query:
        return jsonify(error="missing_query", message="Provide 'query' (JSON body or form field)."), 400
    from rag.retriever import hybrid_search
    results = hybrid_search(query, state.faiss_index, state.chunks, top_k=5)
    return jsonify(results=[{"text": str(chunk), "score": score, **meta} for chunk, score, meta in results])


@bp.get("/whoami")
@api_login_required
def whoami():
    return jsonify(current_user())
