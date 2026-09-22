## What and why

## How was it tested
- [ ] `make check` passes (lint + tests)
- [ ] For retrieval/prompt changes: `python eval/run_eval.py` numbers are not worse (paste them)

## Checklist
- [ ] No document text or secrets in logs or the audit log
- [ ] Untrusted text (documents, model output) is escaped before rendering as HTML
- [ ] Docs / `.env.example` updated if configuration changed
