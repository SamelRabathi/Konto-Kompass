import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.environ["REDIS_URL"]
celery = Celery("portfolio_pulse", broker=REDIS_URL, backend=REDIS_URL)

celery.conf.timezone = "Europe/Berlin"

# täglich 06:00
celery.conf.beat_schedule = {
    "daily-sync-all-tenants": {
        "task": "app.tasks.sync_all_tenants",
        "schedule": crontab(hour=6, minute=0),
    }
}
