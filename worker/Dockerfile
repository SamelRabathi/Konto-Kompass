FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml /app/
COPY app /app/app

RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir .

CMD ["celery", "-A", "app.celery_app:celery", "worker", "-l", "INFO"]
