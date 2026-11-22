from datetime import date
from celery.utils.log import get_task_logger
from app.worker.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.google_oauth import GoogleOAuthConnection
from app.analytics.collection import collect_connection_snapshot

logger = get_task_logger(__name__)

@celery_app.task(name="app.worker.analytics_tasks.collect_all_youtube_analytics", bind=True, max_retries=0)
def collect_all_youtube_analytics(self):
    db = SessionLocal()
    outcomes = {"collected": 0, "failed": 0, "skipped": 0}
    try:
        connection_ids = [row.id for row in db.query(GoogleOAuthConnection.id).all()]
        for connection_id in connection_ids:
            connection = db.get(GoogleOAuthConnection, connection_id)
            if connection is None:
                outcomes["skipped"] += 1
                continue
            try:
                collect_connection_snapshot(db, connection)
                outcomes["collected"] += 1
            except Exception:
                db.rollback()
                outcomes["failed"] += 1
                logger.exception("YouTube analytics collection failed for connection %s", connection_id)
        return outcomes
    finally:
        db.close()

@celery_app.task(name="app.worker.analytics_tasks.collect_user_youtube_analytics", bind=True, max_retries=0)
def collect_user_youtube_analytics(self, user_id: str, period_end: str | None = None):
    db = SessionLocal()
    try:
        connection = db.query(GoogleOAuthConnection).filter_by(user_id=user_id).first()
        if connection is None:
            return {"status": "not_connected"}
        snapshot = collect_connection_snapshot(db, connection, date.fromisoformat(period_end) if period_end else None)
        return {"status": "collected", "snapshot_id": snapshot.id}
    finally:
        db.close()
