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

COPY api/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/docker-entrypoint.sh"]
