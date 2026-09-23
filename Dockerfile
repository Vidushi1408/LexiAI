FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LEXI_LOG_FORMAT=json \
    HF_HOME=/opt/models/hf \
    NLTK_DATA=/opt/models/nltk

# libgomp: required by faiss / torch CPU kernels
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake models into the image so it runs fully offline / on-prem.
# Set --build-arg PRELOAD_NER=1 to also bake in the 1.3 GB BERT NER model.
ARG PRELOAD_NER=0
RUN python -c "import nltk; [nltk.download(p, quiet=True) for p in ('punkt','punkt_tab','stopwords','wordnet','omw-1.4','averaged_perceptron_tagger','averaged_perceptron_tagger_eng')]" \
 && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" \
 && if [ "$PRELOAD_NER" = "1" ]; then python -c "from transformers import pipeline; pipeline('ner', model='dbmdz/bert-large-cased-finetuned-conll03-english')"; fi

COPY . .

# Run as an unprivileged user; /app/data holds the users file, audit log and (optionally) saved indexes
RUN useradd --create-home lexi && mkdir -p /app/data && chown -R lexi:lexi /app /opt/models
USER lexi
VOLUME ["/app/data"]

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD curl -fs http://localhost:8000/healthz || exit 1

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "--timeout", "120", "app:app"]
