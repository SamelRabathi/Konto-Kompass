FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml /app/
COPY app /app/app

RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir .

EXPOSE 8501
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
