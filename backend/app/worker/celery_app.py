from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery('bioinfobeats', broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "daily-youtube-analytics-collection": {
            "task": "app.worker.analytics_tasks.collect_all_youtube_analytics",
            "schedule": crontab(hour=settings.analytics_collection_hour_utc, minute=0),
            "options": {"expires": 3600},
        }
    },
)
celery_app.autodiscover_tasks(['app.worker'])
import app.worker.video_tasks  # noqa: E402,F401
import app.worker.creative_tasks  # noqa: E402,F401
import app.worker.analytics_tasks  # noqa: E402,F401
