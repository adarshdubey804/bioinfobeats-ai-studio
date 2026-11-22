from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.job_run import JobRun
from app.api.deps import get_current_user, get_owned_workflow
from app.worker.production_tasks import assemble_approved_production
from app.api.routes.video import SceneRequest

router = APIRouter()

class AssemblyRequest(BaseModel):
    aspect: str = Field(default="vertical", pattern="^(vertical|landscape)$")
    visual_mode: str = Field(default="auto", pattern="^(auto|static|ai)$")
    scenes: list[SceneRequest] = Field(default_factory=list, max_length=20)
    music_asset_id: str | None = None
    brand_logo_asset_id: str | None = None
    music_volume: float = Field(default=0.12, ge=0, le=0.3)
    voice_id: str | None = Field(default=None, min_length=1, max_length=100)
    voice_stability: float = Field(default=0.48, ge=0, le=1)
    voice_similarity: float = Field(default=0.78, ge=0, le=1)
    voice_speed: float = Field(default=1.0, ge=0.7, le=1.2)
    pronunciation_dictionary: str = Field(default="", max_length=3000)

@router.post("/workflows/{workflow_id}/production/assemble", tags=["production"])
def assemble_production(workflow_id: str, payload: AssemblyRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item=get_owned_workflow(workflow_id,user,db)
    config=item.config or {}
    script=config.get("approved_script") or ""
    if not config.get("research_script_id") or len(script.strip()) < 30:
        raise HTTPException(409,"This workflow has no approved research script. Create it from the Research Studio approval handoff.")
    existing=config.get("production_assembly") or {}
    if existing.get("status") in {"queued","rendering","generating_creatives","retrying"}:
        raise HTTPException(409,"Production assembly is already running.")
    for index, scene in enumerate(payload.scenes, 1):
        from app.api.routes.video import _validate_asset
        _validate_asset(db, user.id, scene.asset_id, {"image", "video"}, f"Scene {index} asset")
    from app.api.routes.video import _validate_asset
    _validate_asset(db, user.id, payload.music_asset_id, {"audio"}, "Background music")
    _validate_asset(db, user.id, payload.brand_logo_asset_id, {"image"}, "Brand logo")
    render_id=str(uuid4())
    job={"id":str(uuid4()),"render_id":render_id,"status":"queued","step":"queued","aspect":payload.aspect,"visual_mode":payload.visual_mode,"created_at":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
    item.config={**config,"approved_title":item.topic,"production_assembly":job,"video_render_request":payload.model_dump(),"video_render":{"id":render_id,"status":"queued","title":item.topic,"aspect":payload.aspect}}
    run = JobRun(id=str(uuid4()), workflow_id=item.id, task_type="production_assembly", status="queued", progress={"stage": "queued", "percent": 0})
    db.add(run)
    db.commit()
    db.refresh(run)
    result = assemble_approved_production.delay(workflow_id, render_id, run.id)
    run.celery_task_id = result.id
    db.commit()
    return {"workflow_id":workflow_id,"job_run_id":run.id,**job,"message":"Approved script queued for narration, storyboard, video rendering, thumbnails and social copy. Review all assets before publishing."}
