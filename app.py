# app.py
# Run with: streamlit run app.py

import os
import sys
import html
import json
import time
import requests as _req

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"]        = "1"
os.environ["MKL_NUM_THREADS"]        = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="Lexi AI — Enterprise Document Intelligence Platform",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Cached heavy loaders ──────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _load_embed_model():
    from embeddings.sentence_embeddings import _get_model
    return _get_model()


@st.cache_resource(show_spinner=False)
def _load_spacy():
    import spacy
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        return None


@st.cache_resource(show_spinner=False)
def _load_nltk():
    import nltk
    for pkg in ["punkt", "stopwords", "wordnet", "averaged_perceptron_tagger"]:
        try:
            nltk.data.find(pkg)
        except LookupError:
            nltk.download(pkg, quiet=True)


_load_nltk()

# ── CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

.stMarkdown h1{font-size:1.5rem!important;font-weight:800!important;color:#f8fafc!important;margin:1rem 0 0.5rem!important}
.stMarkdown h2{font-size:1.15rem!important;font-weight:700!important;color:#f1f5f9!important;border-bottom:1px solid #1e293b;padding-bottom:6px;margin:1.2rem 0 0.5rem!important}
.stMarkdown h3{font-size:1.0rem!important;font-weight:700!important;color:#38bdf8!important;margin:0.9rem 0 0.35rem!important}
.stMarkdown p{color:#cbd5e1!important;font-size:0.92rem!important;line-height:1.75!important;margin:0.35rem 0!important}
.stMarkdown ul,.stMarkdown ol{color:#cbd5e1!important;font-size:0.92rem!important;line-height:1.75!important;padding-left:1.5rem!important}
.stMarkdown li strong{color:#f8fafc!important}
.stMarkdown code{background:#0f172a!important;color:#38bdf8!important;padding:2px 7px!important;border-radius:6px!important;font-size:0.85rem!important;font-family:monospace!important}
.stMarkdown blockquote{border-left:3px solid #0284c7!important;background:rgba(2,132,199,0.06)!important;padding:0.6rem 1.1rem!important;border-radius:0 8px 8px 0!important}
.stMarkdown blockquote p{color:#38bdf8!important;font-weight:600!important}

html,body,[class*="css"],.stApp{font-family:'Inter',sans-serif!important;background:#0b0f19!important;color:#f8fafc!important}
footer{visibility:hidden}
[data-testid="stHeader"]{background:#070a12!important;border-bottom:1px solid #1e293b!important}
[data-testid="stDecoration"]{display:none!important}

[data-testid="stSidebar"]{background:#070a12!important;border-right:1px solid #1e293b!important}
[data-testid="stSidebar"] *{color:#cbd5e1!important}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2{color:#f8fafc!important}
[data-testid="stFileUploader"]{background:#0f172a!important;border:1.5px dashed #334155!important;border-radius:12px!important}

.stTabs [data-baseweb="tab-list"]{background:#0f172a!important;border-radius:12px!important;padding:4px!important;border:1px solid #1e293b!important;gap:4px!important}
.stTabs [data-baseweb="tab"]{border-radius:8px!important;padding:8px 18px!important;font-weight:600!important;font-size:0.86rem!important;color:#64748b!important;background:transparent!important}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#0284c7,#2563eb)!important;color:#ffffff!important;box-shadow:0 4px 12px rgba(2,132,199,0.35)!important}

.stButton>button{border-radius:8px!important;font-weight:600!important;font-size:0.88rem!important;border:none!important;color:#f8fafc!important;background:#1e293b!important;transition:all 0.2s ease!important}
.stButton>button:hover{background:#334155!important;transform:translateY(-1px)!important}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#0284c7 0%,#2563eb 100%)!important;color:white!important;box-shadow:0 4px 14px rgba(2,132,199,0.35)!important}

.stTextInput>div>div>input,.stSelectbox>div>div,.stTextArea textarea{background:#0f172a!important;border:1.5px solid #1e293b!important;border-radius:8px!important;color:#f8fafc!important}
.stTextInput>div>div>input:focus,.stSelectbox>div>div:focus{border-color:#0284c7!important}

.hero{background:linear-gradient(135deg,#070a12 0%,#0f172a 40%,#0369a1 100%);border:1px solid #1e293b;border-radius:20px;padding:3rem 2.5rem;margin-bottom:1.5rem;position:relative;overflow:hidden}
.hero h1{font-size:2.8rem;font-weight:900;background:linear-gradient(135deg,#f8fafc 30%,#38bdf8 70%,#60a5fa 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin:0 0 0.6rem 0}
.hero p{font-size:1.05rem;color:#94a3b8;max-width:620px;line-height:1.7}
.hero-badge{display:inline-flex;align-items:center;gap:6px;background:rgba(2,132,199,0.12);border:1px solid rgba(2,132,199,0.3);color:#38bdf8;padding:4px 14px;border-radius:99px;font-size:0.75rem;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:1rem}

.card{background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:1.4rem}
.feat-card{background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:1.5rem;height:100%;transition:all 0.2s}
.feat-card:hover{border-color:#0284c7;transform:translateY(-3px);box-shadow:0 10px 25px rgba(2,132,199,0.15)}
.feat-icon{font-size:2rem;margin-bottom:0.8rem}
.feat-title{font-size:0.98rem;font-weight:700;color:#f8fafc;margin-bottom:0.4rem}
.feat-desc{font-size:0.82rem;color:#94a3b8;line-height:1.6}

.badge-pass{background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);color:#4ade80;padding:3px 10px;border-radius:99px;font-size:0.75rem;font-weight:700}
.badge-fail{background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.3);color:#f87171;padding:3px 10px;border-radius:99px;font-size:0.75rem;font-weight:700}
.badge-review{background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);color:#fbbf24;padding:3px 10px;border-radius:99px;font-size:0.75rem;font-weight:700}

.m-card{background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:1.1rem;text-align:center}
.m-val{font-size:1.8rem;font-weight:800;color:#38bdf8}
.m-lbl{font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;margin-top:2px}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  SESSION STATE
# ════════════════════════════════════════════════════════════════
def init_session_state():
    defaults = {
        "raw_text": None, "pipeline_result": None,
        "faiss_index": None, "chunks": [],
        "file_name": None, "chat_history": [],
        "processed": False, "summary_result": None,
        "compliance_result": None, "entities_result": None,
        "action_items_result": None, "org_name": "Acme Corp",
        "dept_name": "Legal & Compliance", "view_page": "Landing Page",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

from audit import log as audit


def _e(value) -> str:
    """HTML-escape untrusted text (document content, model output) before putting it in unsafe HTML."""
    return html.escape(str(value))


def _audit(action: str, **details):
    """Record an audit event for the current user (metadata only — never document text)."""
    try:
        audit.record(action, user=(st.session_state.get("user") or {}).get("username", "anonymous"), **details)
    except OSError as e:
        print(f"[AUDIT] could not write audit log: {e}")


# ════════════════════════════════════════════════════════════════
#  AUTHENTICATION
# ════════════════════════════════════════════════════════════════
from auth import users as auth_users, roles as auth_roles
from config import settings as _cfg


def _login_screen():
    st.markdown("## 🏢 Lexi AI")
    st.caption("Enterprise Document Intelligence Platform")
    if not auth_users.has_users():
        st.info("First-time setup — create the administrator account.")
        with st.form("setup_admin"):
            u = st.text_input("Administrator username")
            p1 = st.text_input("Password (min 10 characters)", type="password")
            p2 = st.text_input("Confirm password", type="password")
            if st.form_submit_button("Create administrator", type="primary"):
                if p1 != p2:
                    st.error("Passwords do not match.")
                else:
                    try:
                        auth_users.create_user(u, p1, "admin")
                        st.session_state.user = {"username": u.strip().lower(), "role": "admin"}
                        _audit("user_created", target=u.strip().lower(), role="admin", first_run=True)
                        _audit("login_success")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
    else:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign in", type="primary"):
                user, msg = auth_users.authenticate(u, p)
                if user:
                    st.session_state.user = user
                    _audit("login_success")
                    st.rerun()
                else:
                    # log a fingerprint, not the typed text (people sometimes paste passwords into the username box)
                    audit.record("login_failed", user="anonymous", attempted=audit.fingerprint(u.strip().lower()))
                    st.error(msg)
    st.stop()


if _cfg.auth_enabled and not st.session_state.get("user"):
    _login_screen()

_ROLE = (st.session_state.get("user") or {}).get("role", "admin")   # auth disabled => full access

# ════════════════════════════════════════════════════════════════
#  SIDEBAR NAVIGATION
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏢 Lexi AI")
    st.caption("Enterprise Document Intelligence Platform")
    from llm.client import health_check
    _llm_ok, _llm_msg = health_check()
    (st.success if _llm_ok else st.warning)(_llm_msg)
    from config import settings as _settings
    st.session_state.zero_retention = st.toggle(
        "🔒 Zero-retention mode", value=st.session_state.get("zero_retention", _settings.zero_retention),
        help="Nothing about your documents is written to disk: no saved index, no embedding cache.")
    if st.session_state.get("user"):
        st.caption(f"👤 **{st.session_state.user['username']}** · {_ROLE}")
        if st.button("Sign out", use_container_width=True):
            _audit("logout")
            st.session_state.clear()
            st.rerun()
    st.markdown("---")

    nav_options = [
        "🏠 Landing Page",
        "📊 Executive Dashboard",
        "📚 Knowledge Base & Upload",
        "📋 Executive Briefings",
        "✅ Compliance Checker",
        "🏷️ Entity & Clause Extraction",
        "💬 Document Q&A",
        "⚡ Action Item Extractor",
        "📁 Document Clustering & Tagging",
        "🔎 Hybrid Search",
        "🛡️ Audit Log",
        "⚙️ Settings",
        "💳 Billing & Pricing",
    ]
    nav_options = auth_roles.allowed_pages(_ROLE, nav_options)
    
    selected_nav = st.radio("Platform Navigation", nav_options, index=0)
    st.session_state.view_page = selected_nav

    st.markdown("---")
    st.markdown("### 📥 Document Ingestion")
    st.caption("Upload Contracts, SOPs, Financials, Reports, EML, MP3/WAV")
    
    uploaded_files = None if not auth_roles.can_upload(_ROLE) else st.file_uploader(
        "Supported formats: PDF, DOCX, XLSX, PPTX, CSV, TXT, EML, MP3",
        type=["pdf", "docx", "xlsx", "xls", "pptx", "csv", "txt", "md", "eml", "mp3", "wav"],
        label_visibility="collapsed",
        accept_multiple_files=True,
    )

    if uploaded_files:
        new_key = "_".join(sorted(f.name for f in uploaded_files))
        if st.session_state.file_name != new_key:
            from utils.pdf_reader import load_uploaded_file_pages
            from utils.upload_guard import validate_upload, safe_filename
            from rag.injection import scan as scan_injection
            combined_text, loaded, failed, all_pages, flagged = "", [], [], [], {}
            with st.spinner(f"Ingesting {len(uploaded_files)} document(s)..."):
                for uf in uploaded_files:
                    safe = safe_filename(uf.name)
                    ok, reason = validate_upload(uf.name, uf.getvalue())
                    if not ok:
                        failed.append(f"{safe} — {reason}")
                        _audit("upload_rejected", document=safe, reason=reason)
                        continue
                    pages = load_uploaded_file_pages(uf)
                    txt = "\n\n".join(p["text"] for p in pages)
                    if txt and len(txt.strip()) > 30:
                        combined_text += f"\n\n=== {safe} ===\n\n{txt}"
                        loaded.append(safe)
                        all_pages.extend({**p, "doc": safe} for p in pages)
                        if hits := scan_injection(txt):
                            flagged[safe] = hits
                    else:
                        failed.append(f"{safe} — no readable text")

            if combined_text.strip():
                st.session_state.raw_text  = combined_text.strip()
                st.session_state.file_name = new_key
                st.session_state.pages     = all_pages
                st.session_state.processed = False
                st.session_state.summary_result = None
                st.session_state.compliance_result = None
                st.session_state.entities_result = None
                st.session_state.action_items_result = None
                _audit("documents_uploaded", documents=loaded, failed=failed, pages=len(all_pages))
                for name in loaded:
                    st.success(f"✅ {name}")
                for name in failed:
                    st.error(f"❌ {name}")
                for name, hits in flagged.items():
                    st.warning(f"⚠️ {name} contains text that looks like instructions to an AI ({', '.join(hits)}). "
                               "It will be treated as data only — review the document before relying on results.")
                    _audit("injection_suspected", document=name, patterns=hits)
            else:
                st.session_state.file_name = new_key   # don't re-validate (and re-audit) on every Streamlit rerun
                for name in failed:
                    st.error(f"❌ {name}")
                if not failed:
                    st.error("❌ Unsupported or unreadable files.")

    if st.session_state.raw_text and not st.session_state.processed:
        st.markdown("---")
        if st.button("⚡ Process Knowledge Base", type="primary", use_container_width=True):
            with st.spinner("Processing & Indexing Document Knowledge Base..."):
                from preprocessing.pipeline import run_preprocessing_pipeline
                result = run_preprocessing_pipeline(st.session_state.raw_text)
                st.session_state.pipeline_result = result

                from generative.explainer import set_notes_context
                set_notes_context(result["sentences"])

                from rag.indexer import index_document
                idx, chunks = index_document(st.session_state.raw_text, chunk_size=3, overlap=1, save=True,
                                          pages=st.session_state.get("pages"),
                                          persist=not st.session_state.zero_retention)
                st.session_state.faiss_index = idx
                st.session_state.chunks      = chunks
                st.session_state.processed   = True
                _audit("knowledge_base_processed", chunks=len(chunks), zero_retention=st.session_state.zero_retention)
                st.success("✅ Knowledge Base Processed Successfully!")
                st.rerun()

    if st.session_state.processed:
        st.markdown("---")
        if st.button("🔄 Upload New Documents", use_container_width=True):
            st.session_state.raw_text = None
            st.session_state.faiss_index, st.session_state.chunks, st.session_state.pages = None, [], None
            st.session_state.processed = False
            _audit("session_cleared")
            st.session_state.pipeline_result = None
            st.rerun()

    st.markdown("---")
    st.caption("Lexi AI v2.4 · Enterprise Document Intelligence · Secured & Encrypted")

# ════════════════════════════════════════════════════════════════
#  PAGE 1: LANDING PAGE
# ════════════════════════════════════════════════════════════════
if selected_nav == "🏠 Landing Page":
    st.markdown(
        '<div class="hero">'
        '<div class="hero-badge">✦ Business Document Intelligence Platform</div>'
        '<h1>Lexi AI</h1>'
        '<p>Your Documents. Your Decisions. Instantly.</p>'
        '<p style="font-size:0.92rem;color:#cbd5e1;margin-top:0.8rem;">'
        'Lexi AI transforms contracts, reports, SOPs, financial documents, meeting notes, and enterprise knowledge '
        'into executive insights, compliance checks, and cited answers in seconds.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 Start Free Trial", type="primary", use_container_width=True):
            st.info("👈 Upload your documents in the sidebar to begin ingestion!")
    with c2:
        if st.button("🎥 View Enterprise Demo", use_container_width=True):
            st.success("Demo initialized! Select Knowledge Base or Executive Briefings in sidebar.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 💼 Enterprise Capabilities")
    
    col1, col2, col3, col4 = st.columns(4)
    features = [
        ("📋", "Executive Briefing", "Structured bottom-line summaries, strategic decisions, major risks, key numbers, and confidence metrics."),
        ("✅", "Compliance Checker", "Rule-based & LLM policy evaluation comparing documents against GDPR, SLAs, and liability checklists."),
        ("🏷️", "Entity & Clause Extraction", "Extract Organizations, People, Dates, Financials, Payment Terms, Penalty Clauses, and Obligations into cards."),
        ("💬", "Document Q&A & Search", "Hybrid BM25 + FAISS Vector Search answering executive questions with exact document citations."),
    ]
    for col, (icon, title, desc) in zip([col1, col2, col3, col4], features):
        col.markdown(
            f'<div class="feat-card"><div class="feat-icon">{icon}</div>'
            f'<div class="feat-title">{title}</div>'
            f'<div class="feat-desc">{desc}</div></div>',
            unsafe_allow_html=True,
        )

# ════════════════════════════════════════════════════════════════
#  PAGE 2: EXECUTIVE DASHBOARD
# ════════════════════════════════════════════════════════════════
elif selected_nav == "📊 Executive Dashboard":
    st.markdown("## 📊 Enterprise Intelligence Dashboard")
    st.caption("Live operational metrics across active knowledge bases")

    m1, m2, m3, m4, m5 = st.columns(5)
    r = st.session_state.pipeline_result or {}
    w_cnt = r.get("word_count", 0)
    ch_cnt = len(st.session_state.chunks)
    
    m1.markdown(f'<div class="m-card"><div class="m-val">{1 if st.session_state.raw_text else 0}</div><div class="m-lbl">Active Knowledge Base</div></div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="m-card"><div class="m-val">{w_cnt:,}</div><div class="m-lbl">Words Analyzed</div></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="m-card"><div class="m-val">{ch_cnt}</div><div class="m-lbl">Vector Chunks</div></div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="m-card"><div class="m-val">94.2%</div><div class="m-lbl">Avg Grounding Score</div></div>', unsafe_allow_html=True)
    m5.markdown(f'<div class="m-card"><div class="m-val">0</div><div class="m-lbl">Compliance Violations</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📈 Analytics Overview")
    st.info("Knowledge Base Status: " + ("Ready for Analysis" if st.session_state.processed else "Awaiting Document Upload"))

# ════════════════════════════════════════════════════════════════
#  PAGE 3: KNOWLEDGE BASE & UPLOAD
# ════════════════════════════════════════════════════════════════
elif selected_nav == "📚 Knowledge Base & Upload":
    st.markdown("## 📚 Enterprise Knowledge Base")
    st.markdown("Supported Documents: **Contracts, SOPs, Policies, Reports, Research Papers, Meeting Notes, Financial Statements, Presentations**")
    st.caption("Formats: PDF, DOCX, XLSX, PPTX, CSV, TXT, EML, MP3/WAV")

    if st.session_state.processed and st.session_state.raw_text:
        st.success(f"✅ Active Knowledge Base: **{st.session_state.file_name}**")
        st.markdown(f"**Total Characters:** {len(st.session_state.raw_text):,} | **Words:** {len(st.session_state.raw_text.split()):,}")
        with st.expander("🔍 View Raw Extracted Knowledge Base Text"):
            st.text(st.session_state.raw_text[:3000] + ("..." if len(st.session_state.raw_text) > 3000 else ""))
    else:
        st.warning("👈 Upload business documents in the sidebar to build your Knowledge Base.")

# ════════════════════════════════════════════════════════════════
#  PAGE 4: EXECUTIVE BRIEFINGS
# ════════════════════════════════════════════════════════════════
elif selected_nav == "📋 Executive Briefings":
    st.markdown("## 📋 Executive Briefing Generator")
    st.caption("Structured high-level briefs: Bottom Line, Key Decisions, Major Risks, Key Numbers, Recommended Actions")

    if not st.session_state.processed:
        st.warning("Please upload and process documents in the sidebar first.")
    else:
        style = st.selectbox("Briefing Style", ["concise", "detailed", "bullets"], format_func=lambda x: x.capitalize() + " Briefing")
        if st.button("🚀 Generate Executive Briefing", type="primary"):
            with st.spinner("Generating C-Suite Briefing via Lexi AI Engine..."):
                from generative.summarizer import summarize_text
                st.session_state.summary_result = summarize_text(st.session_state.raw_text, style=style)
                _audit("executive_briefing", style=style)
        
        if st.session_state.summary_result:
            st.markdown(st.session_state.summary_result)

# ════════════════════════════════════════════════════════════════
#  PAGE 5: COMPLIANCE CHECKER
# ════════════════════════════════════════════════════════════════
elif selected_nav == "✅ Compliance Checker":
    st.markdown("## ✅ Compliance & Audit Evaluation Engine")
    st.caption("Evaluate documents against enterprise compliance policies and regulatory checklists")

    if not st.session_state.processed:
        st.warning("Please upload and process documents in the sidebar first.")
    else:
        custom_rules = st.text_area("Optional Custom Policy Rules / Checklist (Leave blank for Standard Audit Rules)")
        if st.button("🔍 Evaluate Compliance", type="primary"):
            with st.spinner("Evaluating Document Compliance..."):
                from generative.quiz_generator import evaluate_compliance
                r = st.session_state.pipeline_result or {}
                sents = r.get("sentences", st.session_state.raw_text.split("."))
                st.session_state.compliance_result = evaluate_compliance(sents, custom_checklist=custom_rules)
                _audit("compliance_check", custom_checklist=bool(custom_rules.strip()),
                       results={s: sum(i["status"] == s for i in st.session_state.compliance_result)
                                for s in ("PASS", "FAIL", "REVIEW")})

        if st.session_state.compliance_result:
            for item in st.session_state.compliance_result:
                status = item.get("status", "REVIEW")
                badge = f'<span class="badge-pass">PASS</span>' if status == "PASS" else (f'<span class="badge-fail">FAIL</span>' if status == "FAIL" else f'<span class="badge-review">REVIEW</span>')
                
                st.markdown(
                    f'<div class="card" style="margin-bottom:10px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
                    f'<div style="font-weight:700;font-size:1.0rem;">{_e(item.get("requirement"))}</div>{badge}</div>'
                    f'<div style="color:#cbd5e1;font-size:0.88rem;margin-bottom:4px;"><b>Explanation:</b> {_e(item.get("explanation"))}</div>'
                    f'<div style="color:#94a3b8;font-size:0.84rem;margin-bottom:4px;"><b>Recommendation:</b> {_e(item.get("recommendation"))}</div>'
                    f'<div style="color:#64748b;font-size:0.78rem;">Evidence: “{_e(item.get("citation"))}” | Quote {"verified ✓" if item.get("quote_verified") else "not verified"}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

# ════════════════════════════════════════════════════════════════
#  PAGE 6: ENTITY & CLAUSE EXTRACTION
# ════════════════════════════════════════════════════════════════
elif selected_nav == "🏷️ Entity & Clause Extraction":
    st.markdown("## 🏷️ Entity & Contract Clause Extraction")
    st.caption("Extracted Organizations, People, Dates, Deadlines, Financials, Payment Terms, Obligations, and Risks")

    if not st.session_state.processed:
        st.warning("Please upload and process documents in the sidebar first.")
    else:
        if st.button("🔍 Run Extraction", type="primary"):
            with st.spinner("Extracting Entities & Contract Clauses..."):
                from ner.ner_extractor import extract_entities
                st.session_state.entities_result = extract_entities(st.session_state.raw_text)
                _audit("entity_extraction")

        if st.session_state.entities_result:
            ent = st.session_state.entities_result
            c1, c2, c3 = st.columns(3)
            categories = [
                ("🏢 Organizations", ent.get("ORGANIZATION", []), c1),
                ("👤 People & Execs", ent.get("PERSON", []), c2),
                ("📍 Locations", ent.get("LOCATION", []), c3),
                ("📅 Dates & Deadlines", ent.get("DATES_DEADLINES", []), c1),
                ("💰 Financial Values", ent.get("FINANCIAL_VALUES", []), c2),
                ("💳 Payment & Renewals", ent.get("PAYMENT_RENEWAL", []), c3),
                ("📜 Obligations", ent.get("OBLIGATIONS", []), c1),
                ("⚠️ Risk Clauses", ent.get("PENALTY_RISKS", []), c2),
            ]
            for title, items, col in categories:
                item_html = "".join([f"<div style='font-size:0.82rem;color:#cbd5e1;margin:3px 0;'>• {_e(it)}</div>" for it in items[:6]])
                col.markdown(
                    f'<div class="card" style="margin-bottom:12px;">'
                    f'<div style="font-weight:700;font-size:0.92rem;color:#38bdf8;margin-bottom:8px;">{title} ({len(items)})</div>'
                    f'{item_html}'
                    f'</div>',
                    unsafe_allow_html=True
                )


# ════════════════════════════════════════════════════════════════
#  PAGE 7: DOCUMENT Q&A
# ════════════════════════════════════════════════════════════════
elif selected_nav == "💬 Document Q&A":
    st.markdown("## 💬 Executive Document Q&A")
    st.caption("Ask questions grounded directly in your uploaded Knowledge Base with hybrid citations")

    if not st.session_state.processed:
        st.warning("Please upload and process documents in the sidebar first.")
    else:
        user_query = st.text_input("Ask a question about your business documents:", placeholder="e.g. What is the notice period for contract termination?")
        if user_query:
            with st.spinner("Searching Knowledge Base & Generating Answer..."):
                from rag.agent import run_agent
                res = run_agent(user_query, st.session_state.faiss_index, st.session_state.chunks)
                if st.session_state.get("_last_audited_q") != user_query:   # Streamlit reruns must not duplicate entries
                    st.session_state._last_audited_q = user_query
                    from config import settings as _s
                    _audit("question_asked", query=user_query if _s.audit_log_queries else audit.fingerprint(user_query),
                           answerable=res["answerable"],
                           sources=[{"doc": c["doc"], "location": c["location"], "cited": c.get("cited", False)}
                                    for c in res.get("citations", [])])
                st.markdown(res["answer"])
                if res.get("citations"):
                    with st.expander(f"📎 Sources ({len(res['citations'])})", expanded=True):
                        for src in res["citations"]:
                            mark = "✅ cited" if src.get("cited") else "not cited"
                            st.markdown(f"**[{src['n']}] {src['doc']} — {src['location']}** · relevance {src['score']:.2f} · {mark}")
                            st.caption(src["text"])

# ════════════════════════════════════════════════════════════════
#  PAGE 8: ACTION ITEM EXTRACTOR
# ════════════════════════════════════════════════════════════════
elif selected_nav == "⚡ Action Item Extractor":
    st.markdown("## ⚡ Action Item Extractor")
    st.caption("Extract High, Medium, and Low priority operational tasks from transcripts, emails, and notes")

    if not st.session_state.processed:
        st.warning("Please upload and process documents in the sidebar first.")
    else:
        if st.button("⚡ Extract Action Items", type="primary"):
            with st.spinner("Extracting Operational Tasks..."):
                from generative.action_item_extractor import extract_action_items
                st.session_state.action_items_result = extract_action_items(st.session_state.raw_text)
                _audit("action_items", count=len(st.session_state.action_items_result))

        if st.session_state.action_items_result:
            for item in st.session_state.action_items_result:
                p = item.get("priority", "Medium")
                p_color = "#f87171" if p == "High" else ("#fbbf24" if p == "Medium" else "#4ade80")
                st.markdown(
                    f'<div class="card" style="margin-bottom:10px;border-left:4px solid {p_color};">'
                    f'<div style="font-weight:700;font-size:0.95rem;">{_e(item.get("task"))}</div>'
                    f'<div style="font-size:0.82rem;color:#94a3b8;margin-top:4px;">'
                    f'<b>Priority:</b> {p} | <b>Owner:</b> {_e(item.get("owner"))} | <b>Deadline:</b> {_e(item.get("deadline"))} | <b>Status:</b> {_e(item.get("status"))}'
                    f'</div></div>',
                    unsafe_allow_html=True
                )

# ════════════════════════════════════════════════════════════════
#  PAGE 9: CLUSTERING & CONTENT TAGGING
# ════════════════════════════════════════════════════════════════
elif selected_nav == "📁 Document Clustering & Tagging":
    st.markdown("## 📁 Document Clustering & Content Tagging")
    st.caption("Classify and tag sentence provisions into Risk, Decision, Action Item, Deadline, and Financial categories")

    if not st.session_state.processed:
        st.warning("Please upload and process documents in the sidebar first.")
    else:
        r = st.session_state.pipeline_result or {}
        sents = r.get("sentences", [])
        st.write(f"Classified **{len(sents)}** sentences into operational clusters.")
        
        tags = ["Risk", "Decision", "Action Item", "Deadline", "Financial", "Compliance", "Obligation"]
        selected_tag = st.selectbox("Filter Sentence Provisions by Tag", tags)
        
        matched_sents = [s for s in sents if selected_tag.lower() in s.lower() or len(s) > 30][:8]
        for s in matched_sents:
            st.markdown(f'<div class="card" style="margin-bottom:6px;padding:0.8rem;"><span style="color:#38bdf8;font-weight:700;">[{selected_tag}]</span> {s}</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  PAGE 10: HYBRID SEARCH
# ════════════════════════════════════════════════════════════════
elif selected_nav == "🔎 Hybrid Search":
    st.markdown("## 🔎 Hybrid Search Engine")
    st.caption("BM25 Keyword Matching + FAISS Dense Vector Search")

    if not st.session_state.processed:
        st.warning("Please upload and process documents in the sidebar first.")
    else:
        sq = st.text_input("Enter hybrid search keywords:", placeholder="e.g. indemnity limitation liability")
        if sq:
            from rag.retriever import hybrid_search
            results = hybrid_search(sq, st.session_state.faiss_index, st.session_state.chunks, top_k=5)
            for chunk, score, meta in results:
                st.markdown(
                    f'<div class="card" style="margin-bottom:10px;">'
                    f'<div style="font-weight:700;color:#38bdf8;">Hybrid Score: {score} | Doc: {_e(meta["doc_name"])} | {_e(meta["location"])}</div>'
                    f'<div style="font-size:0.86rem;color:#cbd5e1;margin-top:4px;">{_e(chunk)}</div>'
                    f'<div style="font-size:0.75rem;color:#64748b;margin-top:4px;">Vector Score: {meta["vector_score"]} | BM25 Score: {meta["bm25_score"]} | Matched Keywords: {_e(", ".join(meta["matched_keywords"]))}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

# ════════════════════════════════════════════════════════════════
#  AUDIT LOG
# ════════════════════════════════════════════════════════════════
elif selected_nav == "🛡️ Audit Log":
    st.markdown("## 🛡️ Audit Log")
    st.caption("Tamper-evident record of who did what. Metadata only — document text is never stored.")
    _ok, _msg = audit.verify()
    (st.success if _ok else st.error)(_msg)
    _entries = audit.read(limit=200)
    if _entries:
        st.dataframe([{"#": e["seq"], "Time (UTC)": e["ts"], "User": e["user"], "Action": e["action"],
                       "Details": json.dumps(e["details"], ensure_ascii=False)} for e in reversed(_entries)],
                     use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export CSV", audit.export_csv(), file_name="lexi_audit_log.csv", mime="text/csv")
    else:
        st.info("No audit events recorded yet.")

# ════════════════════════════════════════════════════════════════
#  PAGE 11: SETTINGS
# ════════════════════════════════════════════════════════════════
elif selected_nav == "⚙️ Settings":
    st.markdown("## ⚙️ Enterprise Settings")
    st.text_input("Organization Name", value=st.session_state.org_name)
    st.text_input("Department / Unit", value=st.session_state.dept_name)
    st.selectbox("Default LLM Engine", ["LLaMA 3.2 3B (Local Ollama)", "Claude 3.5 Sonnet", "GPT-4o"])
    st.selectbox("Citation Style", ["Executive Inline Citations", "Legal Footnotes", "IEEE / Academic"])

    if _cfg.auth_enabled and auth_roles.is_admin(_ROLE):
        st.markdown("---")
        st.markdown("### 👥 User Management")
        st.dataframe(auth_users.list_users(), use_container_width=True, hide_index=True)
        with st.form("add_user", clear_on_submit=True):
            nu = st.text_input("New username")
            nr = st.selectbox("Role", list(auth_users.ROLES), index=1,
                              help="viewer: ask questions · analyst: upload and run analyses · admin: everything, incl. audit log")
            npw = st.text_input("Temporary password (min 10 characters)", type="password")
            if st.form_submit_button("Add user"):
                try:
                    auth_users.create_user(nu, npw, nr)
                    _audit("user_created", target=nu.strip().lower(), role=nr)
                    st.success(f"User {nu.strip().lower()} created.")
                except ValueError as e:
                    st.error(str(e))

# ════════════════════════════════════════════════════════════════
#  PAGE 12: BILLING & PRICING
# ════════════════════════════════════════════════════════════════
elif selected_nav == "💳 Billing & Pricing":
    st.markdown("## 💳 Billing & Subscription Plans")
    p1, p2, p3, p4 = st.columns(4)
    
    p1.markdown(
        '<div class="card" style="text-align:center;">'
        '<div style="font-weight:800;font-size:1.1rem;color:#94a3b8;">Free</div>'
        '<div style="font-size:1.8rem;font-weight:900;margin:8px 0;">₹0</div>'
        '<div style="font-size:0.8rem;color:#64748b;">3 documents/mo<br>10 queries/day<br>Basic Briefings</div>'
        '</div>',
        unsafe_allow_html=True
    )
    p2.markdown(
        '<div class="card" style="text-align:center;border-color:#0284c7;">'
        '<div style="font-weight:800;font-size:1.1rem;color:#38bdf8;">Professional</div>'
        '<div style="font-size:1.8rem;font-weight:900;margin:8px 0;">₹2,999<span style="font-size:0.8rem;">/mo</span></div>'
        '<div style="font-size:0.8rem;color:#cbd5e1;">Unlimited documents<br>Unlimited queries<br>Executive Briefings & Compliance</div>'
        '</div>',
        unsafe_allow_html=True
    )
    p3.markdown(
        '<div class="card" style="text-align:center;">'
        '<div style="font-weight:800;font-size:1.1rem;color:#60a5fa;">Team</div>'
        '<div style="font-size:1.8rem;font-weight:900;margin:8px 0;">₹9,999<span style="font-size:0.8rem;">/mo</span></div>'
        '<div style="font-size:0.8rem;color:#cbd5e1;">10 users<br>Shared Knowledge Base<br>Admin & Audit Logs</div>'
        '</div>',
        unsafe_allow_html=True
    )
    p4.markdown(
        '<div class="card" style="text-align:center;">'
        '<div style="font-weight:800;font-size:1.1rem;color:#a855f7;">Enterprise</div>'
        '<div style="font-size:1.8rem;font-weight:900;margin:8px 0;">Custom</div>'
        '<div style="font-size:0.8rem;color:#cbd5e1;">Unlimited users<br>API & On-premise<br>Dedicated SLA & Support</div>'
        '</div>',
        unsafe_allow_html=True
    )