FROM python:3.12-slim

WORKDIR /app

COPY packages/konto_models /packages/konto_models
COPY packages/konto_connectors /packages/konto_connectors
COPY api/pyproject.toml /app/
COPY api/app /app/app
COPY api/alembic /app/alembic
COPY api/alembic.ini /app/alembic.ini

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir /packages/konto_models /packages/konto_connectors \
    && pip install --no-cache-dir .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host=0.0.0.0 --port=8000"]
