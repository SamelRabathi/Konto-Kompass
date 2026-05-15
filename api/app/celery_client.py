import os

from celery import Celery

_redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
_celery = Celery("konto_kompass_api", broker=_redis_url, backend=_redis_url)


def trigger_sync_tenant(tenant_id: int) -> None:
    _celery.send_task("app.tasks.sync_tenant", args=[tenant_id])
