FROM python:3.12-slim

WORKDIR /app

COPY packages/konto_models /packages/konto_models
COPY packages/konto_connectors /packages/konto_connectors
COPY worker/pyproject.toml /app/
COPY worker/app /app/app

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir /packages/konto_models /packages/konto_connectors \
    && pip install --no-cache-dir .

CMD ["celery", "-A", "app.celery_app:celery", "worker", "-l", "INFO"]
