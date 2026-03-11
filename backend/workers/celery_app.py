# backend/workers/celery_app.py
from celery import Celery
from backend.core.config import settings

# Initialize Celery
celery_app = Celery(
    "manualmind_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["backend.workers.tasks"] # Tell Celery where to find our tasks
)

# Optional: Configure Celery settings for production
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1 # Fair dispatching for heavy tasks
)