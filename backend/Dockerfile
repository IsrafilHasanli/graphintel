FROM python:3.12-slim

WORKDIR /srv

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/srv/backend \
    FASTEMBED_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

COPY pyproject.toml README.md /srv/
COPY backend /srv/backend
COPY data /srv/data
COPY scripts /srv/scripts

RUN pip install -e ".[llm,embeddings]" \
    && python -c "import os; from fastembed import TextEmbedding; list(TextEmbedding(model_name=os.environ['FASTEMBED_EMBEDDING_MODEL']).embed(['warmup']))"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]
