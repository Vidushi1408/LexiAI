# generative/quiz_generator.py
"""
Compliance Checker — Lexi AI
Evaluates a business document against a versioned policy checklist (PASS / FAIL / REVIEW).
The LLM is constrained to a JSON schema, and every PASS/FAIL must carry a quote that is
verified to exist in the document — otherwise it is downgraded to REVIEW.
Falls back to a rule-based keyword scan when Ollama is offline.
(Filename kept for import compatibility; `generate_quiz` is a legacy alias.)
"""
import os, sys
import yaml
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm.client import chat_json
from generative.schemas import ComplianceReport
from generative.quote_check import quote_in_text

POLICY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "policies", "standard_contract.yaml")

COMPLIANCE_SYSTEM_PROMPT = """You are an enterprise compliance analyst reviewing a business document.

For EACH checklist item, decide whether the document satisfies it, using ONLY the provided text.
Return one finding per checklist item with:
  requirement    : the checklist item name
  status         : PASS (clearly satisfied), FAIL (clearly violated or contradicted) or REVIEW (missing, ambiguous or needs a human)
  explanation    : 1-2 sentences justifying the status
  recommendation : one concrete next step
  quote          : a VERBATIM excerpt copied from the document that supports the status; empty string if none exists

Rules: never invent clauses or paraphrase inside `quote`. If the evidence is absent, use REVIEW with an empty quote."""


def load_policy(path: str = POLICY_FILE) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _finalize(finding: dict, doc_text: str) -> dict:
    """Map a finding to the UI shape and enforce the verified-quote rule."""
    quote = (finding.get("quote") or "").strip()
    verified = bool(quote) and quote_in_text(quote, doc_text)
    status, explanation = finding["status"], finding["explanation"]
    if status in ("PASS", "FAIL") and not verified:
        status = "REVIEW"
        explanation += " (Downgraded to REVIEW: no verifiable supporting quote in the document.)"
    return {
        "requirement": finding["requirement"], "status": status, "explanation": explanation,
        "recommendation": finding["recommendation"],
        "citation": quote if verified else "Section Not Found",
        "quote_verified": verified,
    }


def _reconcile_with_policy(items: list[dict], policy: dict) -> list[dict]:
    """
    Guarantee one result per standard-policy requirement, in policy order — a small local model
    sometimes returns fewer items than the checklist has, and silently showing a partial list
    would look complete when it isn't. Any requirement the model never addressed becomes an
    explicit REVIEW entry rather than disappearing.
    """
    by_name = {i["requirement"].strip().lower(): i for i in items}
    reconciled = []
    for req in policy["requirements"]:
        match = by_name.get(req["name"].strip().lower()) or next(
            (i for i in items if req["name"].lower() in i["requirement"].lower()
             or i["requirement"].lower() in req["name"].lower()), None)
        reconciled.append(match or {
            "requirement": req["name"], "status": "REVIEW",
            "explanation": "The AI model did not evaluate this requirement — retry the check or review it manually.",
            "recommendation": f"Re-run the compliance check, or have legal confirm {req['name'].lower()}.",
            "citation": "Section Not Found", "quote_verified": False,
        })
    return reconciled


def evaluate_compliance(sentences: list, custom_checklist: str = None) -> list:
    """
    Evaluates document sentences against the standard policy (or a custom checklist).
    Returns a list of dicts: requirement, status, explanation, recommendation, citation, quote_verified.
    For the standard policy, the result always has exactly one entry per checklist requirement —
    see _reconcile_with_policy. A custom checklist has no fixed catalogue to reconcile against,
    so it returns whatever the model addressed.
    """
    if not sentences:
        return []

    doc_text = " ".join(sentences[:80])[:4000]
    policy = load_policy()
    using_custom = bool(custom_checklist and custom_checklist.strip())

    if using_custom:
        checklist = f"Checklist / Policy Rules to verify:\n{custom_checklist.strip()}"
    else:
        checklist = f"{policy['name']} (v{policy['version']}) — verify each item:\n" + "\n".join(
            f"{n}. {r['name']} — {r['description']}" for n, r in enumerate(policy["requirements"], 1))

    user_msg = f"{checklist}\n\nDocument Content to Evaluate:\n{doc_text}"
    report = chat_json(COMPLIANCE_SYSTEM_PROMPT, user_msg, ComplianceReport, max_tokens=3000)

    expected = None if using_custom else len(policy["requirements"])
    if report is not None and expected is not None and len(report.items) < expected:
        retry_msg = (f"{user_msg}\n\nYour previous reply covered only {len(report.items)} of {expected} "
                     f"checklist items. Return all {expected} items this time, one per requirement, in order.")
        report = chat_json(COMPLIANCE_SYSTEM_PROMPT, retry_msg, ComplianceReport, max_tokens=3000) or report

    if report is None or not report.items:
        return _rule_based_compliance_fallback(sentences, policy)

    items = [_finalize(f.model_dump(), doc_text) for f in report.items]
    return items if using_custom else _reconcile_with_policy(items, policy)


def _rule_based_compliance_fallback(sentences: list, policy: dict | None = None) -> list:
    """Offline keyword scan: quotes the first sentence that mentions each requirement."""
    policy = policy or load_policy()
    results = []
    for req in policy["requirements"]:
        hit = next((s for s in sentences if any(k in s.lower() for k in req["keywords"])), None)
        results.append({
            "requirement": req["name"],
            "status": "PASS" if hit else "REVIEW",
            "explanation": ("Relevant clause located by keyword scan (LLM offline) — adequacy not assessed."
                            if hit else f"No provision mentioning {req['name'].lower()} was found."),
            "recommendation": ("Have legal confirm the clause is adequate." if hit
                               else f"Add or confirm a standard clause for {req['name']}."),
            "citation": hit.strip()[:300] if hit else "Section Not Found",
            "quote_verified": bool(hit),
        })
    return results


def generate_quiz(sentences: list, num_questions: int = 5) -> list:
    """Compatibility alias — routes to compliance checker."""
    items = evaluate_compliance(sentences)
    # Convert compliance items to MCQ structure for any legacy callers
    quiz_items = []
    for idx, item in enumerate(items[:num_questions], 1):
        quiz_items.append({
            "question": f"Compliance Audit Point #{idx}: {item['requirement']}",
            "question_type": "compliance_check",
            "options": {
                "A": f"PASS - {item['explanation'][:60]}",
                "B": f"FAIL - {item['recommendation'][:60]}",
                "C": "REVIEW - Requires Manual Legal Review",
                "D": "NOT APPLICABLE"
            },
            "answer": "A" if item["status"] == "PASS" else ("B" if item["status"] == "FAIL" else "C"),
            "explanation": f"[{item['status']}] {item['explanation']} Citation: {item['citation']}",
            "use_image": False,
            "image_url": None,
            "topic": item["requirement"]
        })
    return quiz_items


def format_quiz_for_display(quiz: list) -> str:
    """Formats compliance / quiz items for text display."""
    if not quiz:
        return "No compliance items found."
    lines = ["Compliance Evaluation Report\n", "=" * 60]
    for i, item in enumerate(quiz, 1):
        req = item.get("requirement") or item.get("question", f"Item #{i}")
        status = item.get("status", "REVIEW")
        expl = item.get("explanation", "")
        rec = item.get("recommendation", "")
        lines.append(f"\n{i}. [{status}] {req}")
        lines.append(f"   Explanation: {expl}")
        if rec:
            lines.append(f"   Recommendation: {rec}")
    return "\n".join(lines)
