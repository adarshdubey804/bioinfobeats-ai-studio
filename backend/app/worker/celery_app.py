from celery import Celery
from app.core.config import settings

celery_app = Celery('bioinfobeats', broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
)
celery_app.autodiscover_tasks(['app.worker'])
# This task module has a descriptive filename rather than Celery's default tasks.py.
import app.worker.video_tasks  # noqa: E402,F401
