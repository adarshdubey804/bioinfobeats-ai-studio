from uuid import uuid4
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user, get_owned_workflow
from app.worker.video_tasks import render_workflow_video

router = APIRouter()

class SceneRequest(BaseModel):
    prompt: str = Field(min_length=8, max_length=700)
    duration_seconds: int = Field(default=6, ge=3, le=20)

class VideoRenderRequest(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    script: str = Field(min_length=30, max_length=12000)
    aspect: str = Field(default="vertical", pattern="^(vertical|landscape)$")
    scenes: list[SceneRequest] = Field(default_factory=list, max_length=8)
    music_filename: str | None = Field(default=None, max_length=100)

@router.post("/workflows/{workflow_id}/render", tags=["video"])
def queue_video_render(workflow_id: str, payload: VideoRenderRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = get_owned_workflow(workflow_id, user, db)
    render_id = str(uuid4())
    request = payload.model_dump()
    render = {"id": render_id, "status": "queued", "title": payload.title, "aspect": payload.aspect, "scene_count": len(payload.scenes)}
    item.config = {**(item.config or {}), "video_render": render, "video_render_request": request}
    db.commit()
    render_workflow_video.delay(workflow_id, render_id)
    return {"workflow_id": workflow_id, **render, "message": "Render queued. Review the MP4 before publishing."}
