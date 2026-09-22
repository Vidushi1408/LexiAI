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
| **UI Framework** | Streamlit (Dark SaaS Professional Theme) |
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
├── app.py                          # Main Lexi AI Streamlit Application
├── requirements.txt                # Enterprise Python Dependencies
├── README.md                       # Platform Documentation
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
│   ├── indexer.py                  # Chunking & FAISS Vector indexing
│   ├── retriever.py                # Hybrid Search Engine (BM25 + Vector)
│   ├── qa_chain.py                 # QA Chain helper
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
streamlit run app.py
```

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
