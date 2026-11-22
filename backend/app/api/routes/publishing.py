from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import httpx
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user, get_owned_workflow
from app.publishing.buffer import list_channels, create_post, BufferAPIError, BufferConfigurationError

router = APIRouter()

class PublishApproval(BaseModel):
    channel_id: str = Field(min_length=2, max_length=200)
    text: str = Field(min_length=1, max_length=10000)
    approved: bool
    scheduled_at: datetime | None = None
    publish_now: bool = False

@router.get("/publishing/channels", tags=["publishing"])
def channels(user: User = Depends(get_current_user)):
    try:
        return list_channels()
    except BufferConfigurationError as exc:
        raise HTTPException(503, str(exc))
    except (BufferAPIError, httpx.HTTPError) as exc:
        raise HTTPException(502, f"Buffer channel lookup failed: {exc}")

@router.post("/workflows/{workflow_id}/publishing/approve", tags=["publishing"])
def approve_and_schedule(workflow_id: str, payload: PublishApproval, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = get_owned_workflow(workflow_id, user, db)
    if payload.approved is not True:
        raise HTTPException(400, "Explicit approval is required before sending content to Buffer.")
    if payload.publish_now and payload.scheduled_at is not None:
        raise HTTPException(400, "Choose either publish_now or scheduled_at, not both.")
    due_at = None
    if not payload.publish_now:
        if payload.scheduled_at is None:
            raise HTTPException(400, "scheduled_at is required unless publish_now is true.")
        if payload.scheduled_at.tzinfo is None:
            raise HTTPException(400, "scheduled_at must include a timezone.")
        due_at = payload.scheduled_at.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        if datetime.fromisoformat(due_at.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            raise HTTPException(400, "scheduled_at must be in the future.")
    config = item.config or {}
    existing = config.get("publishing", {})
    if existing.get("status") in {"scheduled", "sent"}:
        raise HTTPException(409, "This workflow already has a Buffer post recorded.")
    try:
        post = create_post(payload.channel_id, payload.text, due_at, payload.publish_now)
    except BufferConfigurationError as exc:
        raise HTTPException(503, str(exc))
    except (BufferAPIError, httpx.HTTPError) as exc:
        raise HTTPException(502, f"Buffer publish request failed: {exc}")
    record = {"status": post.get("status", "submitted"), "post_id": post.get("id"), "channel_id": payload.channel_id, "due_at": post.get("dueAt") or due_at, "external_link": post.get("externalLink"), "approved_at": datetime.now(timezone.utc).isoformat(), "mode": "shareNow" if payload.publish_now else "customScheduled"}
    item.config = {**config, "publishing": record}
    db.commit()
    return {"workflow_id": workflow_id, "publishing": record}
