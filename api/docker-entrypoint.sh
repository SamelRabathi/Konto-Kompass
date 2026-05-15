#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
python <<'PY'
import os
import sys
import time

from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
engine = create_engine(url, pool_pre_ping=True)

for attempt in range(1, 31):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("PostgreSQL is ready.")
        sys.exit(0)
    except Exception as exc:
        print(f"  attempt {attempt}/30: {exc}")
        time.sleep(2)

print("PostgreSQL did not become ready in time.", file=sys.stderr)
sys.exit(1)
PY

echo "Running migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn app.main:app --host=0.0.0.0 --port=8000
