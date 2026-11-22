from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import httpx
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.research_script import ResearchScript
from app.models.script_revision import ScriptRevision
from app.models.workflow import Workflow
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

class ScriptEditRequest(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    script: str = Field(min_length=30, max_length=20000)
    sections: list[dict] | None = None
    change_note: str = Field(default="Saved edit", max_length=500)

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
    return serialize_script(row)

@router.put('/research/scripts/{script_id}', tags=['research'])
def edit_research_script(script_id: str, payload: ScriptEditRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row=db.query(ResearchScript).filter_by(id=script_id,user_id=user.id).first()
    if row is None: raise HTTPException(404,"Research script not found.")
    if row.status == "approved": raise HTTPException(409,"Approved scripts are locked. Create a new draft to make further edits.")
    latest=db.query(ScriptRevision).filter_by(script_id=row.id,user_id=user.id).order_by(ScriptRevision.version.desc()).first()
    version=(latest.version if latest else 1)+1
    db.add(ScriptRevision(script_id=row.id,user_id=user.id,version=version,title=row.title,script=row.script,sections=row.sections,change_note=payload.change_note))
    row.title=payload.title; row.script=payload.script
    if payload.sections is not None: row.sections=payload.sections
    db.commit(); db.refresh(row)
    return {**serialize_script(row),"revision":version}

@router.get('/research/scripts/{script_id}/revisions', tags=['research'])
def list_script_revisions(script_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row=db.query(ResearchScript).filter_by(id=script_id,user_id=user.id).first()
    if row is None: raise HTTPException(404,"Research script not found.")
    revisions=db.query(ScriptRevision).filter_by(script_id=row.id,user_id=user.id).order_by(ScriptRevision.version.desc()).all()
    return [{"id":x.id,"version":x.version,"title":x.title,"word_count":len(x.script.split()),"change_note":x.change_note,"created_at":x.created_at.isoformat()} for x in revisions]

@router.post('/research/scripts/{script_id}/approve', tags=['research'])
def approve_research_script(script_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row=db.query(ResearchScript).filter_by(id=script_id,user_id=user.id).first()
    if row is None: raise HTTPException(404,"Research script not found.")
    if not row.script.strip(): raise HTTPException(409,"Cannot approve an empty script.")
    row.status="approved"; db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status,"approved_at":datetime.now(timezone.utc).isoformat(),"word_count":len(row.script.split()),"estimated_speaking_minutes":round(len(row.script.split())/140,1)}

@router.post('/research/scripts/{script_id}/workflow', tags=['research'])
def handoff_script_to_workflow(script_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row=db.query(ResearchScript).filter_by(id=script_id,user_id=user.id).first()
    if row is None: raise HTTPException(404,"Research script not found.")
    if row.status != "approved": raise HTTPException(409,"Approve the script after scientific review before sending it to production.")
    workflow=Workflow(owner_id=user.id,topic=row.title,status="draft",config={"brand":"BioinfoBeats","audience":row.audience,"format":"YouTube explainer","target_duration_seconds":row.target_duration_minutes*60,"research_script_id":row.id,"approved_script":row.script,"research_sources":row.sources,"claim_audit":row.fact_check})
    db.add(workflow); db.commit(); db.refresh(workflow)
    return {"workflow_id":workflow.id,"topic":workflow.topic,"status":workflow.status,"script":row.script}

@router.get('/research/scripts/{script_id}/revisions/{revision_id}', tags=['research'])
def get_script_revision(script_id: str, revision_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row=db.query(ResearchScript).filter_by(id=script_id,user_id=user.id).first()
    if row is None: raise HTTPException(404,"Research script not found.")
    revision=db.query(ScriptRevision).filter_by(id=revision_id,script_id=script_id,user_id=user.id).first()
    if revision is None: raise HTTPException(404,"Script revision not found.")
    return {"id":revision.id,"version":revision.version,"title":revision.title,"script":revision.script,"sections":revision.sections,"change_note":revision.change_note,"created_at":revision.created_at.isoformat()}

@router.post('/research/scripts/{script_id}/revisions/{revision_id}/restore', tags=['research'])
def restore_script_revision(script_id: str, revision_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row=db.query(ResearchScript).filter_by(id=script_id,user_id=user.id).first()
    if row is None: raise HTTPException(404,"Research script not found.")
    if row.status == "approved": raise HTTPException(409,"Approved scripts are locked. Create a new draft before restoring a revision.")
    revision=db.query(ScriptRevision).filter_by(id=revision_id,script_id=script_id,user_id=user.id).first()
    if revision is None: raise HTTPException(404,"Script revision not found.")
    latest=db.query(ScriptRevision).filter_by(script_id=script_id,user_id=user.id).order_by(ScriptRevision.version.desc()).first()
    next_version=(latest.version if latest else 1)+1
    db.add(ScriptRevision(script_id=row.id,user_id=user.id,version=next_version,title=row.title,script=row.script,sections=row.sections,change_note=f"Before restoring version {revision.version}"))
    row.title=revision.title; row.script=revision.script; row.sections=revision.sections
    db.commit(); db.refresh(row)
    return {**serialize_script(row),"revision":next_version,"restored_from":revision.version}

def serialize_script(row):
    words=len(row.script.split())
    return {"id":row.id,"topic":row.topic,"audience":row.audience,"title":row.title,"script":row.script,"sections":row.sections,"claims":row.claims,"sources":row.sources,"fact_check":row.fact_check,"duration_minutes":row.target_duration_minutes,"word_count":words,"estimated_speaking_minutes":round(words/140,1),"status":row.status,"created_at":row.created_at.isoformat()}
