from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user, get_owned_workflow
from app.worker.creative_tasks import generate_workflow_creatives

router = APIRouter()

class CreativeRequest(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    script: str = Field(min_length=30, max_length=12000)
    platforms: list[str] = Field(default_factory=lambda: ["YouTube", "Instagram", "LinkedIn"], max_length=5)

@router.post("/workflows/{workflow_id}/creative", tags=["creative"])
def queue_creatives(workflow_id: str, payload: CreativeRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = get_owned_workflow(workflow_id, user, db)
    job = {"status": "queued", "title": payload.title}
    item.config = {**(item.config or {}), "creative_request": payload.model_dump(), "creative_package": job}
    db.commit()
    generate_workflow_creatives.delay(workflow_id)
    return {"workflow_id": workflow_id, **job, "message": "Creative package queued for review."}
