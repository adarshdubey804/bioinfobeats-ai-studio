from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.analytics_snapshot import AnalyticsSnapshot
from app.models.content_idea import ContentIdea
from app.models.workflow import Workflow
from app.agents.pipeline import _call_model

router = APIRouter(prefix="/content", tags=["content intelligence"], dependencies=[Depends(get_current_user)])

class IdeaRequest(BaseModel):
    niche: str = Field(default="Bioinformatics education", min_length=3, max_length=200)
    audience: str = Field(default="Bioinformatics learners and life-science researchers", min_length=3, max_length=300)
    count: int = Field(default=8, ge=3, le=15)
    duration_minutes: int = Field(default=5, ge=3, le=6)

class IdeaStatusRequest(BaseModel):
    status: str = Field(pattern="^(idea|planned|in_production|published|archived)$")
    scheduled_date: date | None = None

@router.post("/ideas/generate")
def generate_ideas(payload: IdeaRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    snapshots = db.query(AnalyticsSnapshot).filter_by(user_id=user.id).order_by(AnalyticsSnapshot.created_at.desc()).limit(5).all()
    performance = [{"period_start": x.period_start, "period_end": x.period_end, "report": x.report} for x in snapshots]
    try:
        result = _call_model(
            "content_strategist", "BioinfoBeats Content Intelligence Strategist",
            "Generate a ranked content opportunity list for an educational bioinformatics YouTube channel. Use the supplied analytics only as directional evidence; do not claim trend growth or causal performance from aggregate snapshots. If no useful analytics exist, say so and use evergreen educational demand hypotheses. Prioritize searchable learner problems, clear examples, and a 5-minute explainable scope. Return JSON with ideas array; each idea must include title, topic, rationale, audience, format, score (0-100), search_intent, hook, and suggested_series. Return exactly the requested count.",
            {"brand":"BioinfoBeats","niche":payload.niche,"audience":payload.audience,"requested_count":payload.count,"target_duration_minutes":payload.duration_minutes,"analytics_history":performance}
        )
        ideas = result.get("ideas", [])
        if not isinstance(ideas, list) or not ideas:
            raise ValueError("The model did not return an ideas list.")
        created=[]
        for index, item in enumerate(ideas[:payload.count]):
            title=str(item.get("title") or item.get("topic") or "Untitled idea")[:300]
            topic=str(item.get("topic") or title)[:500]
            row=ContentIdea(user_id=user.id,title=title,topic=topic,rationale=str(item.get("rationale") or "")[:5000],audience=str(item.get("audience") or payload.audience)[:300],format=str(item.get("format") or "YouTube explainer")[:80],target_duration_minutes=payload.duration_minutes,score=max(0,min(100,int(item.get("score",0)))),metadata_json={k:v for k,v in item.items() if k not in {"title","topic","rationale","audience","format","score"}})
            db.add(row); created.append(row)
        db.commit()
        return {"count":len(created),"ideas":[serialize(x) for x in created],"analytics_snapshots_used":len(performance)}
    except Exception as exc:
        db.rollback()
        raise HTTPException(502, f"Content idea generation failed: {exc}")

def serialize(row):
    return {"id":row.id,"title":row.title,"topic":row.topic,"rationale":row.rationale,"audience":row.audience,"format":row.format,"target_duration_minutes":row.target_duration_minutes,"score":row.score,"status":row.status,"scheduled_date":row.scheduled_date,"metadata":row.metadata_json,"created_at":row.created_at.isoformat()}

@router.get("/ideas")
def list_ideas(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows=db.query(ContentIdea).filter_by(user_id=user.id).order_by(ContentIdea.score.desc(),ContentIdea.created_at.desc()).limit(100).all()
    return [serialize(x) for x in rows]

@router.patch("/ideas/{idea_id}")
def update_idea(idea_id: str, payload: IdeaStatusRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row=db.query(ContentIdea).filter_by(id=idea_id,user_id=user.id).first()
    if row is None: raise HTTPException(404,"Content idea not found.")
    row.status=payload.status
    row.scheduled_date=payload.scheduled_date.isoformat() if payload.scheduled_date else None
    db.commit(); db.refresh(row)
    return serialize(row)

@router.post("/ideas/{idea_id}/workflow")
def create_workflow_from_idea(idea_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row=db.query(ContentIdea).filter_by(id=idea_id,user_id=user.id).first()
    if row is None: raise HTTPException(404,"Content idea not found.")
    workflow=Workflow(owner_id=user.id,topic=row.topic,status="draft",config={"brand":"BioinfoBeats","audience":row.audience,"format":"YouTube explainer","target_duration_seconds":row.target_duration_minutes*60,"content_idea_id":row.id,"content_idea_metadata":row.metadata_json})
    db.add(workflow); row.status="in_production"; db.commit(); db.refresh(workflow)
    return {"workflow_id":workflow.id,"topic":workflow.topic,"status":workflow.status}
