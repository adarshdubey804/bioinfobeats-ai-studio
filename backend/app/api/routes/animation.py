from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.rendering.scientific_animation import create_animation

router=APIRouter()
class AnimationRequest(BaseModel):
    title:str=Field(default="",max_length=90)
    nodes:list[dict]=Field(default_factory=list,max_length=10)
    edges:list[dict]=Field(default_factory=list,max_length=20)
    sequences:list[str]=Field(default_factory=list,max_length=6)
    labels:list[str]=Field(default_factory=list,max_length=8)

@router.post("/visuals/animate/{kind}",tags=["scientific-animation"])
def animate_visual(kind:str,payload:AnimationRequest,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    try: return create_animation(kind,payload.model_dump())
    except ValueError as exc: raise HTTPException(422,str(exc))
    except Exception as exc: raise HTTPException(500,"Animation rendering failed. Check FFmpeg availability and server logs.") from exc
