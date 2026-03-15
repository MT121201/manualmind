from celery import Celery
from app.core.config import settings

# Initialize Celery
celery_app = Celery(
    "manualmind_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.document_task",
        "app.workers.tasks.memory_task"
    ]
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