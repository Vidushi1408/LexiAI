# webapp/blueprints/features.py
"""One page per analysis feature: briefing, compliance, entities, Q&A, actions, search, clustering."""
from flask import Blueprint, render_template, request

from audit import log as audit
from config import settings
from webapp.security import analyst_required, audit_event, login_required
from webapp.state import get_state

bp = Blueprint("features", __name__)


@bp.route("/briefings", methods=["GET", "POST"])
@analyst_required
def briefing():
    state = get_state()
    style = request.form.get("style", "concise")
    if request.method == "POST" and state.processed:
        from generative.summarizer import summarize_text
        state.summary_result = summarize_text(state.raw_text, style=style, chunks=state.chunks)
        audit_event("executive_briefing", style=style)
    return render_template("briefing.html", state=state, style=style)


@bp.route("/compliance", methods=["GET", "POST"])
@analyst_required
def compliance():
    state = get_state()
    custom_rules = request.form.get("custom_rules", "")
    if request.method == "POST" and state.processed:
        from generative.quiz_generator import evaluate_compliance
        sents = (state.pipeline_result or {}).get("sentences", state.raw_text.split("."))
        state.compliance_result = evaluate_compliance(sents, custom_checklist=custom_rules)
        audit_event("compliance_check", custom_checklist=bool(custom_rules.strip()),
                    results={s: sum(i["status"] == s for i in state.compliance_result)
                             for s in ("PASS", "FAIL", "REVIEW")})
    return render_template("compliance.html", state=state, custom_rules=custom_rules)


@bp.route("/entities", methods=["GET", "POST"])
@analyst_required
def entities():
    state = get_state()
    if request.method == "POST" and state.processed:
        from ner.ner_extractor import extract_entities
        state.entities_result = extract_entities(state.raw_text)
        audit_event("entity_extraction")

    categories = []
    if state.entities_result:
        e = state.entities_result
        categories = [
            ("🏢", "Organizations", e.get("ORGANIZATION", [])),
            ("👤", "People & Execs", e.get("PERSON", [])),
            ("📍", "Locations", e.get("LOCATION", [])),
            ("📅", "Dates & Deadlines", e.get("DATES_DEADLINES", [])),
            ("💰", "Financial Values", e.get("FINANCIAL_VALUES", [])),
            ("💳", "Payment & Renewals", e.get("PAYMENT_RENEWAL", [])),
            ("📜", "Obligations", e.get("OBLIGATIONS", [])),
            ("⚠️", "Risk Clauses", e.get("PENALTY_RISKS", [])),
        ]
    return render_template("entities.html", state=state, categories=categories)


@bp.route("/qa", methods=["GET", "POST"])
@login_required
def qa():
    state = get_state()
    question, result = "", None
    if request.method == "POST" and state.processed:
        question = request.form.get("question", "").strip()
        if question:
            from rag.agent import run_agent
            result = run_agent(question, state.faiss_index, state.chunks)
            state.qa_confidences.append(result.get("confidence", 0.0))
            if state.last_audited_question != question:
                state.last_audited_question = question
                audit_event("question_asked",
                            query=question if settings.audit_log_queries else audit.fingerprint(question),
                            answerable=result["answerable"],
                            sources=[{"doc": c["doc"], "location": c["location"], "cited": c.get("cited", False)}
                                     for c in result.get("citations", [])])
    return render_template("qa.html", state=state, question=question, result=result)


@bp.route("/actions", methods=["GET", "POST"])
@analyst_required
def actions():
    state = get_state()
    if request.method == "POST" and state.processed:
        from generative.action_item_extractor import extract_action_items
        state.action_items_result = extract_action_items(state.raw_text)
        audit_event("action_items", count=len(state.action_items_result))
    return render_template("actions.html", state=state)


@bp.route("/search", methods=["GET", "POST"])
@login_required
def search():
    state = get_state()
    query, results = "", []
    if request.method == "POST" and state.processed:
        query = request.form.get("query", "").strip()
        if query:
            from rag.retriever import hybrid_search
            results = hybrid_search(query, state.faiss_index, state.chunks, top_k=5)
    return render_template("search.html", state=state, query=query, results=results)


@bp.route("/clustering", methods=["GET", "POST"])
@analyst_required
def clustering():
    state = get_state()
    tags = ["Risk", "Decision", "Action Item", "Deadline", "Financial", "Compliance", "Obligation"]
    tag = request.form.get("tag") or request.args.get("tag") or tags[0]
    sentences = (state.pipeline_result or {}).get("sentences", []) if state.processed else []
    matched = [s for s in sentences if tag.lower() in s.lower() or len(s) > 30][:8]
    return render_template("clustering.html", state=state, tags=tags, tag=tag,
                           total=len(sentences), matched=matched)
