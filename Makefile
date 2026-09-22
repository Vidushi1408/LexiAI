.PHONY: setup run run-prod test lint typecheck eval check docker up

PY ?= python3

setup:            ## create venv and install everything
	$(PY) -m venv venv
	venv/bin/pip install -r requirements-dev.txt
	venv/bin/python -m spacy download en_core_web_sm
	venv/bin/python -c "import nltk; [nltk.download(p) for p in ('punkt','punkt_tab','stopwords','wordnet','omw-1.4','averaged_perceptron_tagger','averaged_perceptron_tagger_eng')]"
	venv/bin/pre-commit install

run:              ## start the app (dev server with reload, http://localhost:8000)
	venv/bin/python app.py

run-prod:         ## start the app with gunicorn, like the Docker image does
	venv/bin/gunicorn -w 2 -b 0.0.0.0:8000 --timeout 120 app:app

test:
	venv/bin/python -m pytest -q

lint:
	venv/bin/ruff check .

typecheck:
	venv/bin/mypy

eval:             ## full retrieval evaluation (needs the embedding model)
	venv/bin/python eval/run_eval.py

check: lint test  ## what CI runs (minus the scans)

docker:
	docker build -t lexi-ai .

up:               ## app + local Ollama
	docker compose up --build
