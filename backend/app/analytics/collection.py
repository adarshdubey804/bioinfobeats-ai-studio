"""Shared analytics collection logic for scheduled and manual runs."""
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.google_oauth import GoogleOAuthConnection
from app.models.analytics_snapshot import AnalyticsSnapshot
from app.analytics.youtube import owner_channel_report

def collect_connection_snapshot(db: Session, connection: GoogleOAuthConnection, period_end: date | None = None) -> AnalyticsSnapshot:
    end = period_end or (date.today() - timedelta(days=1))
    start = end - timedelta(days=6)
    report = owner_channel_report(start, end, connection)
    snapshot = AnalyticsSnapshot(user_id=connection.user_id, period_start=start.isoformat(), period_end=end.isoformat(), report=report)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
