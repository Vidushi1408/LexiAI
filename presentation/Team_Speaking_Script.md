# Lexi AI — Team Speaking Script and Role Notes

Total time: about 15–18 minutes, plus questions. Slide numbers match `Lexi_AI_Judges_Deck.pptx`.

> **Check before you present:** the roles and tasks below are inferred from the project's modules. Each person should edit their section so it matches what they actually did. Anything in [square brackets] is a spot to personalise.

---

## Who speaks when

| Order | Speaker | Role (to confirm) | Slides | ~Time |
|---|---|---|---|---|
| 1 | **Vidushi Bhadauria** | Project Lead, full-stack | 1, 2, 3, 4 | 4 min |
| 2 | **Aryama Sharma** | NLP and retrieval | 5, 8, 9 | 4 min |
| 3 | **Ashi Srivastava** | GenAI and extraction | 6, 7 (entities) | 3 min |
| 4 | **Parth Nawal** | ML classification | 7 (tagging), 10 | 2.5 min |
| 5 | **Simran Karan Bora** | UX, data and quality | 11, 12, 13, 14 | 3.5 min |
| 6 | **Vidushi Bhadauria** | Closing | 15, 16 | 1.5 min |

Hand-offs are written into the script. Say the hand-off line out loud so the switch feels smooth.

---

## One-minute project summary (everyone should know this)

Lexi AI is a web platform that reads a company's documents (contracts, reports, policies) and does four jobs.

1. **Answers questions** about the documents, with the source passages shown.
2. **Checks contracts** against compliance rules.
3. **Pulls out entities** such as parties, dates and amounts.
4. **Tags sentences** by topic (Financial, Legal and so on) and writes **briefings**.

The key design choices:
- It runs on the company's own machine with a local language model (Ollama, llama3.2:3b), so documents never leave the building.
- It is **grounded**: answers cite the chunks they came from, and it refuses when the documents don't contain the answer.
- It has logins, an audit log and billing (Stripe), so it is built as a product and not only as a demo.

---

## The script

### 1. Vidushi: opening (slides 1–2, about 1.5 min)

**Slide 1 (Title)**
"Good [morning/afternoon], judges. We are team Lexi AI: Vidushi, Aryama, Ashi, Parth and Simran. Lexi AI is a document-intelligence platform. You give it your company's documents, and it answers questions about them, checks contracts for compliance, and summarises what matters, all running on your own machine."

**Slide 2 (Problem)**
"Every organisation sits on thousands of pages of contracts and policies. People search them by keyword, which misses meaning, or they paste them into public AI tools, which is a confidentiality risk. And general chatbots will confidently make up an answer when the document says nothing. We wanted a tool that is private, that shows its sources, and that says 'I don't know' when it should."

### 2. Vidushi: idea and architecture (slides 3–4, about 2.5 min)

**Slide 3 (Idea)**
"Our idea has three principles: private by default, grounded in sources, and honest about uncertainty. Everything else follows from these."

**Slide 4 (How it works)**
"The flow has four steps. First, documents are uploaded and split into passages. Second, each passage is turned into a vector so we can search by meaning. Third, at question time we combine keyword search and meaning search, which we call hybrid retrieval, and pass the best passages to the local model. Fourth, the answer is shown with its sources. The same retrieved text feeds the compliance check, entity extraction, tagging and briefings. I built the Flask application, the login system and the overall wiring. Aryama will now show it working."

**Hand-off:** "Aryama will show you the question-answering in action."

### 3. Aryama: Q&A demo, testing and retrieval results (slides 5, 8, 9, about 4 min)

**Slide 5 (Q&A demo)**
"This is a real run on a sample contract. I asked: 'What is the annual fee and how is it paid?' The answer comes back with the source passages underneath, so a reviewer can verify it in seconds. I also asked about uptime guarantees, and it found the clause and the remedy when the guarantee isn't met."

**Slide 8 (How we tested)**
"We didn't want to just say it works, so we built an evaluation set: 85 questions across 5 sectors. 63 have an answer in the documents and 22 deliberately don't, to test whether the system refuses properly. We compared plain keyword search (BM25) against our hybrid retrieval."

**Slide 9 (Retrieval results)**
"Hybrid retrieval raised Recall@1, meaning the right passage is the top result, from 79.4% to 87.3%. Recall@3 went from 92.1% to 96.8%, and Recall@5 from 95.2% to 98.4%. MRR rose from 0.862 to 0.919. Hybrid is better on Recall@1 in three of five sectors (consulting, healthcare and legal), and it is never worse than keyword search on any measure."

**Hand-off:** "Ashi will show what we do with those retrieved passages."

### 4. Ashi: compliance, briefings, entities (slides 6–7, about 3 min)

**Slide 6 (Compliance and briefing)**
"The compliance module takes a contract and checks it against six rules. Each rule is marked PASS, REVIEW or FAIL, with the supporting text. Because a small local model has variation, we ran it eight times on the same contract. It passed between 0 and 4 of the 6 checks, about 2 on average, and never gave a FAIL. We report that range openly instead of showing only the best run. The briefing feature writes a summary and cites the source chunks. It did so in 6 of 8 runs, and when it doesn't, the app shows a warning that the briefing carries no source citations."

**Slide 7 (Entities)**
"Entity extraction pulls out the parties, dates, amounts and obligations from a document and shows them in a table, so someone can scan a 30-page contract in a minute."

**Hand-off:** "Parth will explain how we tag content by topic."

### 5. Parth: tagging models (slide 7 tagging half, slide 10, about 2.5 min)

**Slide 7 (Tagging)**
"Tagging assigns each sentence a label such as Financial, Legal or Operational. In the app you can filter a document by tag and see only the financial sentences, for example."

**Slide 10 (Refusal and tagger charts)**
"We trained three neural models on 280 labelled sentences, 40 for each of 7 tags, split 218 for training and 31 each for validation and test, with 80 epochs. The results on the test set: the feed-forward network (ANN) reached 83.9% accuracy, the CNN 77.4%, and the LSTM 48.4%. Chance is 14.3%. The simple ANN won because our dataset is small, and bigger sequence models need more data. We are honest that this is a small dataset, and it is the first thing we would grow."

"On refusal, which is deciding when to say 'not in the documents': keyword search scored 54.5% balanced accuracy, our hybrid method at its default setting scored 75.5%, and with its threshold tuned it reached 95.4%. That tuned figure is on the same data we tuned on, so treat it as an upper bound."

**Hand-off:** "Simran will cover the limits, trust and where we go next."

### 6. Simran: limits, trust, comparison, roadmap (slides 11–14, about 3.5 min)

**Slide 11 (Limits)**
"We want to be upfront about the limits. The local model is small, so compliance results vary from run to run. The tagger is trained on 280 sentences. The refusal threshold was tuned on the same data we evaluated on. And our test set is 85 questions, which is good for a prototype but not a final benchmark."

**Slide 12 (Trust)**
"Trust is built into the product. Every action is written to an audit log, with logins and roles, and an admin can reset passwords. There are 163 automated tests, and on every push our CI runs lint, type checks, a security scan and a Docker build. I checked the interface for readability and error handling, and built the sample data and quality checks behind our evaluation."

**Slide 13 (Comparison)**
"Compared with a generic chatbot and a plain keyword search tool, Lexi AI is the only one that is private, shows its sources, refuses when it doesn't know, and has audit and billing."

**Slide 14 (Roadmap)**
"Next steps: single sign-on, a decision on multi-tenancy, production deployment, observability, a larger tagging dataset, and a stronger model option for customers who allow it."

**Hand-off:** "Vidushi will close."

### 7. Vidushi: team and close (slides 15–16, about 1.5 min)

**Slide 15 (Team)**
"Here is who built what." Introduce each person in one line, using the role cards below. Let each person wave or say their name.

**Slide 16 (Closing)**
"To sum up: Lexi AI answers from your documents, shows its sources, refuses when it doesn't know, and keeps everything on your own machine. It beats keyword search on Recall@1 by 7.9 points, and it is never worse. We measured it, we reported where it varies, and we know what to improve next. Thank you. We are happy to take questions."

---

## Role cards (basic knowledge for each member)

Everyone should be able to answer the "know this" bullets for their own area, and the one-line version for everyone else's.

### Vidushi Bhadauria: Project Lead and full-stack
- **Tasks:** Flask application and page structure, login and roles, password change and admin reset, history of past answers and searches, database migrations (Alembic), the embedding-cache fix, Stripe billing with a Free-plan seat limit, and wiring the tagging model into the app.
- **Know this:** how a request flows from upload to answer; why caches are keyed on the model as well as the text (so switching models can't serve stale vectors); what the Free-plan seat limit does.
- **One-liner:** "I built the application and tied all the modules together."

### Aryama Sharma: NLP and retrieval
- **Tasks:** document chunking, embeddings (MiniLM), BM25 and hybrid retrieval, the refusal threshold, the 85-question evaluation set and the metrics.
- **Know this:**
  - **Recall@k:** how often the right passage is in the top k results.
  - **MRR:** the average of 1 divided by the rank of the right passage.
  - **Hybrid:** it combines keyword score and meaning score.
  - **Refusal:** the system declines when the best match is below a threshold.
- **One-liner:** "I made search find the right passage and know when there isn't one."

### Ashi Srivastava: GenAI and extraction
- **Tasks:** prompts and calls to the local LLM (Ollama, llama3.2:3b), the compliance checklist (6 checks), briefing generation with source citations, entity extraction.
- **Know this:** why we use a local model (privacy); why results vary (small model, sampling); what PASS, REVIEW and FAIL mean; why we show the citation warning.
- **One-liner:** "I turned retrieved text into compliance checks, briefings and extracted facts."

### Parth Nawal: ML classification
- **Tasks:** the labelled 280-sentence dataset (7 tags × 40), training the ANN, CNN and LSTM, and comparing them.
- **Know this:**
  - **ANN:** a simple feed-forward network on sentence embeddings.
  - **CNN:** looks for local word patterns.
  - **LSTM:** reads in sequence and needs more data.
  - **Why ANN won:** small dataset.
  - **Split:** 218 / 31 / 31.
  - **Chance:** 14.3% (1 in 7).
- **One-liner:** "I trained and compared the models that tag sentences by topic."

### Simran Karan Bora: UX, data and quality
- **Tasks:** interface design and usability, sample documents and test data, quality checks, test coverage, and documenting results.
- **Know this:** 163 tests pass locally, and CI runs 156 because 7 torch-based tests are skipped there; what CI checks (lint, types, security scan, Docker build); where the audit log lives.
- **One-liner:** "I made it usable and made sure it keeps working."

---

## Likely judge questions: who answers

| Question | Answer | Who |
|---|---|---|
| Why a local model instead of GPT or similar? | Privacy: documents never leave the machine. A stronger model is a roadmap option. | Vidushi or Ashi |
| What stops it from making things up? | Answers must cite retrieved passages. Below the threshold it refuses. | Aryama |
| Your compliance results vary. Why? | Small local model, so output varies. 0–4 of 6 checks passed across 8 runs, never a FAIL. We report the range honestly. | Ashi |
| Is 280 sentences enough? | No, it is a prototype. The ANN reached 83.9%, well above 14.3% chance. Growing the dataset is next. | Parth |
| Is the 95.4% refusal accuracy real? | It is tuned on the same data, so it is an upper bound. The untuned hybrid is 75.5%. | Aryama |
| Does it scale to many customers? | Not yet. Multi-tenancy and deployment are on the roadmap. | Vidushi or Simran |
| How do you know it won't break? | 163 tests, and CI on every push. | Simran |
| What is the business model? | Stripe billing with a Free plan limited by seats and paid tiers. | Vidushi |

---

## Delivery tips
- Speak to the judges, not the slide. Each slide has one message; say it in your own words.
- If a number is on the slide, you can say it once and move on.
- When asked about a weakness, answer plainly ("yes, that's a limit, and here is what we'd do") instead of defending it.
- If a live demo fails, the deck has real screenshots from actual runs.
