from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import httpx
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.research_script import ResearchScript
from app.research.providers import web_search, youtube_search, ResearchConfigurationError
from app.research.studio import create_research_script

router = APIRouter(dependencies=[Depends(get_current_user)])

class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    max_results: int = Field(default=5, ge=1, le=10)

class ResearchStudioRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    audience: str = Field(default="Bioinformatics learners and life-science researchers", min_length=3, max_length=300)
    duration_minutes: int = Field(default=5, ge=5, le=6)
    include_youtube: bool = True

@router.post('/research/web', tags=['research'])
def search_web(payload: ResearchRequest):
    try: return web_search(payload.query, payload.max_results)
    except ResearchConfigurationError as exc: raise HTTPException(503, str(exc))
    except httpx.HTTPError as exc: raise HTTPException(502, f'Web research provider error: {exc}')

@router.post('/research/youtube', tags=['research'])
def search_youtube(payload: ResearchRequest):
    try: return youtube_search(payload.query, payload.max_results)
    except ResearchConfigurationError as exc: raise HTTPException(503, str(exc))
    except httpx.HTTPError as exc: raise HTTPException(502, f'YouTube research provider error: {exc}')

@router.post('/research/studio', tags=['research'])
def research_studio(payload: ResearchStudioRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        result = create_research_script(payload.topic, payload.audience, payload.duration_minutes, payload.include_youtube)
        row = ResearchScript(user_id=user.id, topic=payload.topic, audience=payload.audience, target_duration_minutes=payload.duration_minutes, title=result["title"], script=result["script"], sections=result["sections"], claims=result["claims"], sources=result["sources"], fact_check=result["fact_check"], status="draft")
        db.add(row); db.commit(); db.refresh(row)
        return {"id":row.id, **result, "status":row.status, "created_at":row.created_at.isoformat()}
    except ResearchConfigurationError as exc:
        db.rollback(); raise HTTPException(503, str(exc))
    except httpx.HTTPError as exc:
        db.rollback(); raise HTTPException(502, f"Research provider error: {exc}")
    except ValueError as exc:
        db.rollback(); raise HTTPException(422, str(exc))
    except Exception as exc:
        db.rollback(); raise HTTPException(502, f"Research and script generation failed: {exc}")

@router.get('/research/scripts', tags=['research'])
def list_research_scripts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows=db.query(ResearchScript).filter_by(user_id=user.id).order_by(ResearchScript.created_at.desc()).limit(50).all()
    return [{"id":x.id,"topic":x.topic,"title":x.title,"duration_minutes":x.target_duration_minutes,"word_count":len(x.script.split()),"status":x.status,"created_at":x.created_at.isoformat()} for x in rows]

@router.get('/research/scripts/{script_id}', tags=['research'])
def get_research_script(script_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row=db.query(ResearchScript).filter_by(id=script_id,user_id=user.id).first()
    if row is None: raise HTTPException(404,"Research script not found.")
    return {"id":row.id,"topic":row.topic,"audience":row.audience,"title":row.title,"script":row.script,"sections":row.sections,"claims":row.claims,"sources":row.sources,"fact_check":row.fact_check,"duration_minutes":row.target_duration_minutes,"status":row.status,"created_at":row.created_at.isoformat()}
