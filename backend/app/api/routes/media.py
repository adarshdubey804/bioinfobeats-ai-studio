import re
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
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


def _matches_signature(content: bytes, media_type: str, content_type: str) -> bool:
    """Reject common MIME-spoofed uploads before persisting them."""
    if media_type == "image":
        return (
            (content_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff"))
            or (content_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n"))
            or (content_type == "image/webp" and len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP")
        )
    if media_type == "audio":
        return (
            (content_type in {"audio/wav", "audio/x-wav"} and len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WAVE")
            or (content_type == "audio/ogg" and content.startswith(b"OggS"))
            or (content_type == "audio/mpeg" and (content.startswith(b"ID3") or (len(content) >= 2 and content[0] == 0xFF and content[1] & 0xE0 == 0xE0)))
        )
    if media_type == "video":
        return (
            (content_type == "video/mp4" and len(content) >= 12 and content[4:8] == b"ftyp")
            or (content_type == "video/webm" and content.startswith(b"\x1a\x45\xdf\xa3"))
        )
    return False


def _item(asset: MediaAsset):
    return {"id": asset.id, "filename": asset.filename, "media_type": asset.media_type,
            "content_type": asset.content_type, "size_bytes": asset.size_bytes,
            "created_at": asset.created_at.isoformat(), "url": f"/api/v1/media/library/{asset.id}/file"}


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
    if not _matches_signature(content, media_type, content_type):
        raise HTTPException(415, "File contents do not match the declared media type.")
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


@router.get("/media/library/{asset_id}/file", tags=["media-library"])
def get_asset_file(asset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    asset = db.scalar(select(MediaAsset).where(MediaAsset.id == asset_id, MediaAsset.user_id == user.id))
    if asset is None:
        raise HTTPException(404, "Media asset not found.")
    root = Path(settings.media_storage_dir).resolve()
    folder = (root / "library" / str(user.id)).resolve()
    path = (folder / asset.storage_name).resolve()
    if root not in folder.parents or folder not in path.parents or not path.is_file():
        raise HTTPException(404, "Media asset file not found.")
    return FileResponse(path, media_type=asset.content_type, filename=asset.filename, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


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
