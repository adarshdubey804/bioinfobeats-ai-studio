from datetime import date
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import httpx
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.google_oauth import GoogleOAuthConnection
from app.models.analytics_snapshot import AnalyticsSnapshot
from app.analytics.youtube import public_video_stats, owner_channel_report, AnalyticsConfigurationError
from app.analytics.collection import collect_connection_snapshot
from app.worker.analytics_tasks import collect_user_youtube_analytics
from app.agents.pipeline import _call_model

router = APIRouter(dependencies=[Depends(get_current_user)])

class VideoStatsRequest(BaseModel):
    video_ids: list[str] = Field(min_length=1, max_length=50)
class ChannelReportRequest(BaseModel):
    start_date: date
    end_date: date
class InsightsRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=300)
    videos: list[dict] = Field(min_length=1, max_length=50)

@router.post("/analytics/youtube/videos", tags=["analytics"])
def youtube_video_stats(payload: VideoStatsRequest):
    try: return public_video_stats(payload.video_ids)
    except AnalyticsConfigurationError as exc: raise HTTPException(503, str(exc))
    except ValueError as exc: raise HTTPException(400, str(exc))
    except httpx.HTTPError as exc: raise HTTPException(502, f"YouTube Data API error: {exc}")

@router.post("/analytics/youtube/channel", tags=["analytics"])
def youtube_channel_report(payload: ChannelReportRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    connection = db.query(GoogleOAuthConnection).filter_by(user_id=user.id).first()
    if connection is None: raise HTTPException(409, "Connect your YouTube channel in Settings before requesting private analytics.")
    try: return owner_channel_report(payload.start_date, payload.end_date, connection)
    except ValueError as exc: raise HTTPException(400, str(exc))
    except httpx.HTTPError as exc: raise HTTPException(502, f"YouTube Analytics API error: {exc}")

@router.post("/analytics/youtube/collect", tags=["analytics"])
def queue_analytics_collection(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    connection = db.query(GoogleOAuthConnection).filter_by(user_id=user.id).first()
    if connection is None: raise HTTPException(409, "Connect your YouTube channel before collecting analytics.")
    task = collect_user_youtube_analytics.delay(user.id)
    return {"status": "queued", "task_id": task.id}

@router.get("/analytics/history", tags=["analytics"])
def analytics_history(limit: int = 30, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if limit < 1 or limit > 100: raise HTTPException(400, "limit must be between 1 and 100.")
    rows = db.query(AnalyticsSnapshot).filter_by(user_id=user.id).order_by(AnalyticsSnapshot.created_at.desc()).limit(limit).all()
    return [{"id": row.id, "period_start": row.period_start, "period_end": row.period_end, "report": row.report, "created_at": row.created_at.isoformat()} for row in rows]

@router.post("/analytics/insights", tags=["analytics"])
def performance_insights(payload: InsightsRequest):
    try:
        return _call_model("performance_analyst", "BioinfoBeats Performance Analyst", "Analyze only supplied video metrics. Identify relative winners, patterns and three experiments. Do not claim causality or infer missing metrics. Return JSON with summary, top_performers, patterns, experiments, limitations.", {"topic": payload.topic, "video_metrics": payload.videos, "brand": "BioinfoBeats"})
    except Exception as exc: raise HTTPException(502, f"Performance analysis failed: {exc}")
