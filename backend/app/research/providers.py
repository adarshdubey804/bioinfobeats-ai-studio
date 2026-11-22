"""Provider adapters for evidence collection. No fabricated results or citations."""
from typing import Any
import httpx
from app.core.config import settings

class ResearchConfigurationError(RuntimeError):
    pass

def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    if not settings.tavily_api_key:
        raise ResearchConfigurationError("TAVILY_API_KEY is not configured.")
    response = httpx.post(
        "https://api.tavily.com/search",
        json={"api_key": settings.tavily_api_key, "query": query, "max_results": max(1, min(max_results, 10)), "search_depth": "basic", "include_answer": False},
        timeout=settings.research_timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    results = []
    for item in data.get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("content", ""),
            "score": item.get("score"),
            "published_date": item.get("published_date"),
        })
    return {"provider": "tavily", "query": query, "results": results}

def youtube_search(query: str, max_results: int = 5) -> dict[str, Any]:
    if not settings.youtube_api_key:
        raise ResearchConfigurationError("YOUTUBE_API_KEY is not configured.")
    response = httpx.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={"key": settings.youtube_api_key, "part": "snippet", "q": query, "type": "video", "maxResults": max(1, min(max_results, 10)), "order": "relevance"},
        timeout=settings.research_timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    results = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        video_id = item.get("id", {}).get("videoId")
        results.append({
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt"),
            "description": snippet.get("description", ""),
            "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
        })
    return {"provider": "youtube_data_api", "query": query, "results": results}
