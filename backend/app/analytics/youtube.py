"""YouTube public video statistics and owner-only Analytics API reports."""
from datetime import date
from typing import Any
import httpx
from app.core.config import settings

class AnalyticsConfigurationError(RuntimeError):
    pass

def public_video_stats(video_ids: list[str]) -> dict[str, Any]:
    if not settings.youtube_api_key:
        raise AnalyticsConfigurationError("YOUTUBE_API_KEY is not configured.")
    if not video_ids or len(video_ids) > 50:
        raise ValueError("Provide between 1 and 50 YouTube video IDs.")
    response = httpx.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part": "snippet,statistics,contentDetails", "id": ",".join(video_ids), "key": settings.youtube_api_key},
        timeout=settings.research_timeout_seconds,
    )
    response.raise_for_status()
    items = []
    for video in response.json().get("items", []):
        stats = video.get("statistics", {})
        views, likes, comments = (int(stats.get(k, 0)) for k in ("viewCount", "likeCount", "commentCount"))
        items.append({
            "video_id": video["id"],
            "title": video.get("snippet", {}).get("title", ""),
            "published_at": video.get("snippet", {}).get("publishedAt"),
            "duration": video.get("contentDetails", {}).get("duration"),
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement_rate": round((likes + comments) / views * 100, 2) if views else 0.0,
            "source": "youtube_data_api_public_statistics",
        })
    return {"videos": items, "count": len(items)}

def owner_channel_report(start_date: date, end_date: date) -> dict[str, Any]:
    if not settings.youtube_oauth_access_token:
        raise AnalyticsConfigurationError("YOUTUBE_OAUTH_ACCESS_TOKEN is required for private channel analytics.")
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date.")
    response = httpx.get(
        "https://youtubeanalytics.googleapis.com/v2/reports",
        headers={"Authorization": f"Bearer {settings.youtube_oauth_access_token}"},
        params={
            "ids": "channel==MINE",
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "metrics": "views,likes,comments,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained",
        },
        timeout=settings.research_timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    return {"column_headers": data.get("columnHeaders", []), "rows": data.get("rows", []), "source": "youtube_analytics_api_owner_report"}
