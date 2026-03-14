# app/workers/celery_app.py
import asyncio
from celery import Celery
from app.core.config import settings
from app.db.connections import db_manager
from celery.signals import worker_process_init, worker_shutdown

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

# Global loop for all tasks to share
worker_loop = None

@worker_process_init.connect
def init_worker_connections(**kwargs):
    global worker_loop
    worker_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(worker_loop)
    worker_loop.run_until_complete(db_manager.connect())

@worker_shutdown.connect
def on_worker_shutdown(**kwargs):
    if worker_loop:
        worker_loop.run_until_complete(db_manager.close())
        worker_loop.close()

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