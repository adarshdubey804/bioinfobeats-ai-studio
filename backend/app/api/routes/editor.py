import json
import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.media_asset import MediaAsset
from app.api.deps import get_current_user, get_owned_workflow

router=APIRouter()

class SceneEdit(BaseModel):
    prompt: str = Field(min_length=8,max_length=700)
    narration_excerpt: str = Field(default="",max_length=1200)
    transition: str = Field(default="fade",pattern="^(cut|fade)$")
    duration_seconds: float | None = Field(default=None,ge=1,le=180)
    overlay_text: str = Field(default="",max_length=90)
    asset_id: str | None = None

class StoryboardEdit(BaseModel):
    scenes: list[SceneEdit] = Field(min_length=2,max_length=20)
    brand_logo_asset_id: str | None = None
    music_asset_id: str | None = None

def _manifest(item, user, db):
    config=item.config or {}
    render=config.get("video_render") or {}
    render_id=render.get("id")
    if not render_id or not re.fullmatch(r"[a-f0-9-]{8,64}",render_id):
        raise HTTPException(409,"Render a video first to create an editable storyboard.")
    root=Path(settings.media_storage_dir).resolve()
    folder=(root/render_id).resolve()
    if root not in folder.parents: raise HTTPException(400,"Invalid render path.")
    path=folder/"storyboard.json"
    if not path.is_file(): raise HTTPException(404,"Storyboard not found for this render.")
    try: data=json.loads(path.read_text(encoding="utf-8"))
    except (ValueError,OSError): raise HTTPException(500,"Storyboard manifest could not be read.")
    return render_id,folder,path,data

@router.get("/workflows/{workflow_id}/editor/storyboard",tags=["video-editor"])
def get_storyboard(workflow_id:str,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    item=get_owned_workflow(workflow_id,user,db)
    render_id,folder,path,data=_manifest(item,user,db)
    scenes=[]
    for index,scene in enumerate(data.get("scenes",[])):
        image=folder/f"scene-{index+1:02}.png"
        motion=folder/f"motion-{index+1:02}.mp4"
        scenes.append({**scene,"index":index,"preview_url":f"/media/{render_id}/{image.name}" if image.is_file() else None,"motion_url":f"/media/{render_id}/{motion.name}" if motion.is_file() else None})
    return {"render_id":render_id,"title":data.get("title"),"aspect":data.get("aspect"),"visual_mode":data.get("visual_mode","auto"),"audio_duration_seconds":data.get("audio_duration_seconds"),"music_volume":data.get("music_volume",0.12),"brand_logo_asset_id":data.get("brand_logo_asset_id"),"music_asset_id":data.get("music_asset_id"),"scenes":scenes}

@router.put("/workflows/{workflow_id}/editor/storyboard",tags=["video-editor"])
def save_storyboard(workflow_id:str,payload:StoryboardEdit,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    item=get_owned_workflow(workflow_id,user,db)
    render_id,folder,path,data=_manifest(item,user,db)
    if payload.brand_logo_asset_id:
        logo=db.scalar(select(MediaAsset).where(MediaAsset.id==payload.brand_logo_asset_id,MediaAsset.user_id==user.id,MediaAsset.media_type=="image"))
        if logo is None: raise HTTPException(422,"Brand logo must be an image in your media library.")
    if payload.music_asset_id:
        music=db.scalar(select(MediaAsset).where(MediaAsset.id==payload.music_asset_id,MediaAsset.user_id==user.id,MediaAsset.media_type=="audio"))
        if music is None: raise HTTPException(422,"Background music must be audio in your media library.")
    data["brand_logo_asset_id"]=payload.brand_logo_asset_id
    data["music_asset_id"]=payload.music_asset_id
    for index, scene in enumerate(payload.scenes,1):
        if scene.asset_id:
            asset=db.scalar(select(MediaAsset).where(MediaAsset.id==scene.asset_id,MediaAsset.user_id==user.id,MediaAsset.media_type.in_({"image","video"})))
            if asset is None: raise HTTPException(422,f"Scene {index} asset must be an image or video in your media library.")
    data["scenes"]=[scene.model_dump() for scene in payload.scenes]
    data["edited_at"]=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    return {"render_id":render_id,"scene_count":len(data["scenes"]),"status":"saved","message":"Storyboard saved. Queue a new render to apply scene edits to the final MP4."}
