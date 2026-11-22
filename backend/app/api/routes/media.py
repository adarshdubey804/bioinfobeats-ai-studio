import re
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.media_asset import MediaAsset
from app.models.user import User

router = APIRouter()
MAX_BYTES = 50 * 1024 * 1024
ALLOWED = {
    "image": {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"},
    "audio": {"audio/mpeg": ".mp3", "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/ogg": ".ogg"},
    "video": {"video/mp4": ".mp4", "video/webm": ".webm"},
}

def _item(asset: MediaAsset):
    return {"id": asset.id, "filename": asset.filename, "media_type": asset.media_type,
            "content_type": asset.content_type, "size_bytes": asset.size_bytes,
            "created_at": asset.created_at.isoformat(), "url": f"/media/library/{asset.user_id}/{asset.storage_name}"}

@router.get("/media/library", tags=["media-library"])
def list_assets(q: str = Query(default="", max_length=100), media_type: str = Query(default="all", pattern="^(all|image|audio|video)$"),
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(MediaAsset).where(MediaAsset.user_id == user.id)
    if media_type != "all":
        stmt = stmt.where(MediaAsset.media_type == media_type)
    if q.strip():
        stmt = stmt.where(MediaAsset.filename.ilike(f"%{q.strip()}%"))
    rows = db.scalars(stmt.order_by(MediaAsset.created_at.desc()).limit(200)).all()
    return [_item(row) for row in rows]

@router.post("/media/library", tags=["media-library"])
async def upload_asset(file: UploadFile = File(...), media_type: str = Query(..., pattern="^(image|audio|video)$"),
                      db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    content_type = (file.content_type or "").lower()
    extension = ALLOWED[media_type].get(content_type)
    if not extension:
        raise HTTPException(415, "Unsupported file type. Upload JPEG, PNG, WebP, MP3, WAV, OGG, MP4 or WebM.")
    original = Path(file.filename or "asset").name
    safe_name = re.sub(r"[^A-Za-z0-9._ -]", "_", original).strip(" .")[:240] or "asset"
    content = await file.read(MAX_BYTES + 1)
    await file.close()
    if not content:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "Maximum upload size is 50 MB.")
    storage_name = f"{uuid.uuid4().hex}{extension}"
    folder = (Path(settings.media_storage_dir).resolve() / "library" / str(user.id)).resolve()
    root = Path(settings.media_storage_dir).resolve()
    if root not in folder.parents:
        raise HTTPException(400, "Invalid media storage path.")
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / storage_name
    destination.write_bytes(content)
    asset = MediaAsset(user_id=user.id, filename=safe_name, storage_name=storage_name,
                       media_type=media_type, content_type=content_type, size_bytes=len(content))
    try:
        db.add(asset)
        db.commit()
        db.refresh(asset)
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    return _item(asset)

@router.delete("/media/library/{asset_id}", tags=["media-library"])
def delete_asset(asset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    asset = db.scalar(select(MediaAsset).where(MediaAsset.id == asset_id, MediaAsset.user_id == user.id))
    if asset is None:
        raise HTTPException(404, "Media asset not found.")
    folder = (Path(settings.media_storage_dir).resolve() / "library" / str(user.id)).resolve()
    path = (folder / asset.storage_name).resolve()
    if folder not in path.parents:
        raise HTTPException(400, "Invalid media storage path.")
    path.unlink(missing_ok=True)
    db.delete(asset)
    db.commit()
    return {"deleted": True, "id": asset_id}
