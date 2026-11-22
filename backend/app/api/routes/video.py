from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.media_asset import MediaAsset
from app.api.deps import get_current_user, get_owned_workflow
from app.worker.video_tasks import render_workflow_video

router = APIRouter()

class SceneRequest(BaseModel):
    prompt: str = Field(min_length=8, max_length=700)
    narration_excerpt: str = Field(default="", max_length=1200)
    transition: str = Field(default="fade", pattern="^(cut|fade)$")
    duration_seconds: float | None = Field(default=None, ge=1, le=180)
    overlay_text: str = Field(default="", max_length=90)
    asset_id: str | None = None

class VideoRenderRequest(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    script: str = Field(min_length=30, max_length=12000)
    aspect: str = Field(default="vertical", pattern="^(vertical|landscape)$")
    scenes: list[SceneRequest] = Field(default_factory=list, max_length=20)
    music_filename: str | None = Field(default=None, max_length=100)
    music_asset_id: str | None = None
    brand_logo_asset_id: str | None = None
    visual_mode: str = Field(default="auto", pattern="^(auto|static|ai)$")
    music_volume: float = Field(default=0.12, ge=0, le=0.3)
    voice_id: str | None = Field(default=None, min_length=1, max_length=100)
    voice_stability: float = Field(default=0.48, ge=0, le=1)
    voice_similarity: float = Field(default=0.78, ge=0, le=1)
    voice_speed: float = Field(default=1.0, ge=0.7, le=1.2)
    pronunciation_dictionary: str = Field(default='', max_length=3000)

def _validate_asset(db: Session, user_id: str, asset_id: str | None, allowed: set[str], label: str):
    if not asset_id:
        return
    asset = db.scalar(select(MediaAsset).where(MediaAsset.id == asset_id, MediaAsset.user_id == user_id))
    if asset is None:
        raise HTTPException(404, f"{label} was not found in your media library.")
    if asset.media_type not in allowed:
        raise HTTPException(422, f"{label} must be one of: {', '.join(sorted(allowed))}.")
    
@router.post("/workflows/{workflow_id}/render", tags=["video"])
def queue_video_render(workflow_id: str, payload: VideoRenderRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = get_owned_workflow(workflow_id, user, db)
    for index, scene in enumerate(payload.scenes, 1):
        _validate_asset(db, user.id, scene.asset_id, {"image", "video"}, f"Scene {index} asset")
    _validate_asset(db, user.id, payload.music_asset_id, {"audio"}, "Background music")
    _validate_asset(db, user.id, payload.brand_logo_asset_id, {"image"}, "Brand logo")
    render_id = str(uuid4())
    request = payload.model_dump()
    render = {"id": render_id, "status": "queued", "title": payload.title, "aspect": payload.aspect, "scene_count": len(payload.scenes), "visual_mode": payload.visual_mode, "storyboard": "auto" if not payload.scenes else "provided"}
    item.config = {**(item.config or {}), "video_render": render, "video_render_request": request}
    db.commit()
    render_workflow_video.delay(workflow_id, render_id)
    return {"workflow_id": workflow_id, **render, "message": "Render queued. Review the MP4 before publishing."}
