from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx
from app.research.providers import web_search, youtube_search, ResearchConfigurationError

router = APIRouter()

class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    max_results: int = Field(default=5, ge=1, le=10)

@router.post('/research/web', tags=['research'])
def search_web(payload: ResearchRequest):
    try:
        return web_search(payload.query, payload.max_results)
    except ResearchConfigurationError as exc:
        raise HTTPException(503, str(exc))
    except httpx.HTTPError as exc:
        raise HTTPException(502, f'Web research provider error: {exc}')

@router.post('/research/youtube', tags=['research'])
def search_youtube(payload: ResearchRequest):
    try:
        return youtube_search(payload.query, payload.max_results)
    except ResearchConfigurationError as exc:
        raise HTTPException(503, str(exc))
    except httpx.HTTPError as exc:
        raise HTTPException(502, f'YouTube research provider error: {exc}')
