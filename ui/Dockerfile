FROM python:3.12-slim

WORKDIR /app

COPY ui/pyproject.toml /app/
COPY ui/app /app/app

RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir .

CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
