from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.rendering.scientific_visuals import generate_visual

router=APIRouter()
class VisualRequest(BaseModel):
    title:str=Field(default="",max_length=100)
    nodes:list[dict]=Field(default_factory=list,max_length=16)
    edges:list[dict]=Field(default_factory=list,max_length=32)
    sequences:list[str]=Field(default_factory=list,max_length=8)
    labels:list[str]=Field(default_factory=list,max_length=12)

@router.post("/visuals/{kind}",tags=["scientific-visuals"])
def create_visual(kind:str,payload:VisualRequest,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    try: return generate_visual(kind,payload.model_dump())
    except ValueError as exc: raise HTTPException(422,str(exc))
