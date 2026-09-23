# 🏢 Lexi AI — Enterprise Document Intelligence Platform

> **Your Documents. Your Decisions. Instantly.**
> Transform contracts, SOPs, financial statements, reports, emails, and meeting transcripts into executive briefings, compliance checks, risk extraction, and cited answers in seconds.

---

## 📌 Core Platform Features

| Capability | Description |
|------------|-------------|
| 📋 **Executive Briefing** | Structured C-Suite briefs with *Bottom Line*, *Key Decisions*, *Major Risks*, *Key Numbers*, *Recommended Actions*, and *Confidence Scores*. |
| ✅ **Compliance Checker** | Evaluate business documents against regulatory policies (GDPR, CCPA, SLAs, Liability Caps) with PASS/FAIL/REVIEW statuses and recommendations. |
| 🏷️ **Entity & Clause Extraction** | Extract Organizations, People, Dates, Deadlines, Financial Values, Payment Terms, Penalty Clauses, Obligations, and Risk Clauses into visual cards. |
| ⚡ **Action Item Extractor** | Categorize tasks from meeting transcripts, emails, and notes into High, Medium, and Low priorities with Owner, Deadline, and Status tags. |
| 💬 **Document Q&A & RAG** | Multi-tool document intelligence agent answering executive questions with exact document citations and confidence scores. |
| 🔎 **Hybrid Search** | Combine **BM25 keyword matching** and **FAISS dense vector search** with score blending and keyword highlights. |
| 📚 **Multi-Format Knowledge Base** | Ingest **PDF, DOCX, XLSX, PPTX, CSV, TXT, MD, EML, and Audio (MP3/WAV)** with Whisper AI transcription. |
| 📊 **Executive Dashboard** | Live operational metrics across active knowledge bases, compliance issue tracking, and knowledge coverage. |

---

## 🛠️ Architecture & Tech Stack

| Layer | Technology |
|-------|-----------|
| **UI Framework** | Flask · Jinja2 server-rendered pages (Dark SaaS Professional Theme), served by gunicorn |
| **NLP Preprocessing** | NLTK · spaCy · Regex |
| **Text Classification** | PyTorch · ANN · CNN · LSTM |
| **Sentence Embeddings** | SentenceTransformers (`all-MiniLM-L6-v2`) |
| **Named Entity Recognition** | BERT (`dbmdz/bert-large-cased-finetuned-conll03-english`) + Lexi Rule Extractors |
| **Vector Indexing & Search** | FAISS + Rank-BM25 (Hybrid Search Engine) |
| **Generative LLM Engine** | Ollama (LLaMA 3.2 3B / Mistral) |
| **Document Ingestion** | PyMuPDF · python-docx · openpyxl · python-pptx · pandas · email · Whisper AI |

---

## 📁 Repository Structure

```
LEXI AI/
│
├── app.py                          # Flask entrypoint (`python app.py`, or gunicorn app:app)
├── config.py                       # Central settings (env vars / .env)
├── requirements.txt                # Enterprise Python Dependencies
├── README.md                       # Platform Documentation
│
├── webapp/                         # Flask application: one page per feature
│   ├── __init__.py                 # App factory (create_app)
│   ├── state.py                    # Per-session knowledge-base state
│   ├── security.py                 # Login/role decorators, CSRF, audit helper
│   ├── uploads.py                  # Adapts Flask uploads to the reader/validator
│   ├── markdown_utils.py           # Sanitised markdown rendering for LLM output
│   ├── blueprints/                 # auth · main (dashboard/audit/settings) · kb · features
│   ├── templates/                  # Jinja2 pages (base.html + one per feature)
│   └── static/css/style.css        # Design system
│
├── auth/                           # Local users (scrypt), roles (viewer/analyst/admin)
├── audit/                          # Tamper-evident (hash-chained) audit log
│
├── preprocessing/                  # Text Cleaning & Tokenization Pipeline
│   ├── cleaner.py                  # Noise removal & regex cleaning
│   ├── tokeniser.py                # Tokenization & stopword removal
│   ├── lemmatizer.py               # Lemmatization & POS tagging
│   └── pipeline.py                 # Pipeline orchestrator
│
├── embeddings/                     # Vector Representations
│   ├── one_hot.py                  # One-hot & Bag-of-Words encoders
│   └── sentence_embeddings.py      # SentenceTransformers (384-dim vectors)
│
├── models/                         # Provision & Text Classification
│   ├── training_data.py            # Sentence dataset
│   ├── data_prep.py                # Data split helper
│   ├── ann_model.py                # Artificial Neural Network
│   ├── cnn_model.py                # Convolutional Neural Network
│   ├── lstm_model.py               # Long Short-Term Memory Network
│   ├── evaluator.py                # Evaluation metrics
│   ├── train_all.py                # Model training suite
│   └── saved/                      # Model checkpoints
│
├── ner/
│   └── ner_extractor.py            # BERT NER + Business & Contract Clause Extractor
│
├── generative/                     # Business Intelligence Generators
│   ├── summarizer.py               # Executive Briefing generator
│   ├── quiz_generator.py           # Compliance Checker engine
│   ├── explainer.py                # Clause & Provision explainer
│   └── action_item_extractor.py    # Action Item Extractor from transcripts/emails
│
├── rag/                            # Retrieval-Augmented Generation
│   ├── indexer.py                  # Chunking & FAISS Vector indexing (keeps true page provenance)
│   ├── retriever.py                # Hybrid Search Engine (BM25 + Vector)
│   ├── citations.py                # Numbered sources + citation verification
│   ├── injection.py                # Prompt-injection heuristic scan on uploads
│   └── agent.py                    # Multi-tool Agentic Document Q&A loop
│
├── utils/
│   ├── pdf_reader.py               # Multi-format reader (PDF, DOCX, XLSX, PPTX, CSV, EML, MP3)
│   └── file_handler.py             # Data persistence utilities
│
└── data/                           # Active Knowledge Base storage
```

---

## ⚙️ Quickstart Guide

### Setup Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run Lexi AI Platform

```bash
python app.py                # dev server with auto-reload, http://localhost:8000
# or, like production:
gunicorn -w 2 -b 0.0.0.0:8000 --timeout 120 app:app
```

The first visit prompts you to create the administrator account. See `.env.example` for configuration
(login, zero-retention mode, upload limits, the LLM endpoint, and `LEXI_SECRET_KEY` for the session cookie).

### Local LLM Engine (Optional for Generative Features)

```bash
ollama serve
ollama pull llama3.2:3b
```

---

## 🧑‍💻 Development

```bash
make setup      # venv, dependencies, spaCy/NLTK data, pre-commit hooks
make check      # lint + tests (what CI runs)
make eval       # retrieval / refusal evaluation on the labelled dataset
make run        # start the app
make up         # app + local Ollama via Docker Compose
```

Configuration is via environment variables — see `.env.example`. Set `LEXI_LOG_FORMAT=json` for structured logs.
CI (`.github/workflows/ci.yml`) runs lint, unit tests, a retrieval-quality gate, type checks, secret scanning (gitleaks),
dependency auditing (pip-audit) and a Docker build on every push and pull request.
