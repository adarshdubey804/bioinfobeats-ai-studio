import logging
import shutil
from pathlib import Path
from app.worker.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.workflow import Workflow
from app.models.media_asset import MediaAsset
from app.rendering.service import render_video
from app.core.config import settings

logger = logging.getLogger(__name__)


def _persist_progress(workflow_id: str, render_id: str, progress: dict) -> None:
    session = SessionLocal()
    try:
        item = session.get(Workflow, workflow_id)
        if item is None:
            return
        config = item.config or {}
        current = config.get("video_render") or {}
        if current.get("id") != render_id:
            return
        item.config = {**config, "video_render": {**current, "status": "rendering", "progress": progress}}
        session.commit()
    finally:
        session.close()

def _prepare_assets(db, user_id, render_id, request):
    root = Path(settings.media_storage_dir).resolve()
    job_dir = (root / render_id).resolve()
    if root not in job_dir.parents:
        raise ValueError("Invalid render output path.")
    job_dir.mkdir(parents=True, exist_ok=True)
    scene_paths = {}
    for index, scene in enumerate(request.get("scenes") or []):
        asset_id = scene.get("asset_id")
        if not asset_id:
            continue
        asset = db.get(MediaAsset, asset_id)
        if asset is None or asset.user_id != user_id or asset.media_type not in {"image", "video"}:
            raise ValueError(f"Scene {index + 1} media asset is missing or not accessible.")
        source = (root / "library" / str(user_id) / asset.storage_name).resolve()
        if root not in source.parents or not source.is_file():
            raise ValueError(f"Scene {index + 1} media file is missing.")
        destination = job_dir / f"scene-asset-{index + 1:02}{source.suffix.lower()}"
        shutil.copy2(source, destination)
        scene_paths[index] = str(destination)
    music_path = None
    music_id = request.get("music_asset_id")
    if music_id:
        asset = db.get(MediaAsset, music_id)
        if asset is None or asset.user_id != user_id or asset.media_type != "audio":
            raise ValueError("Background music is missing or not accessible.")
        source = (root / "library" / str(user_id) / asset.storage_name).resolve()
        if root not in source.parents or not source.is_file():
            raise ValueError("Background music file is missing.")
        destination = job_dir / f"background-music{source.suffix.lower()}"
        shutil.copy2(source, destination)
        music_path = destination.name
    logo_path = None
    logo_id = request.get("brand_logo_asset_id")
    if logo_id:
        asset = db.get(MediaAsset, logo_id)
        if asset is None or asset.user_id != user_id or asset.media_type != "image":
            raise ValueError("Brand logo is missing or not accessible.")
        source = (root / "library" / str(user_id) / asset.storage_name).resolve()
        if root not in source.parents or not source.is_file():
            raise ValueError("Brand logo file is missing.")
        destination = job_dir / f"brand-logo{source.suffix.lower()}"
        shutil.copy2(source, destination)
        logo_path = str(destination)
    return scene_paths, music_path, logo_path

@celery_app.task(name="app.worker.video_tasks.render_workflow_video", bind=True, max_retries=2, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=300, retry_jitter=True)
def render_workflow_video(self, workflow_id: str, render_id: str):
    db = SessionLocal()
    try:
        item = db.get(Workflow, workflow_id)
        if not item:
            return {"status": "not_found"}
        config = item.config or {}
        request = config.get("video_render_request")
        if not request or config.get("video_render", {}).get("id") != render_id:
            return {"status": "superseded"}
        item.config = {**config, "video_render": {**config["video_render"], "status": "rendering", "attempt": self.request.retries + 1}}
        db.commit()
        try:
            scene_paths, music_path, logo_path = _prepare_assets(db, item.owner_id, render_id, request)
            progress_callback = lambda progress: _persist_progress(workflow_id, render_id, progress)
            url = render_video(render_id, request["title"], request["script"], request["aspect"], request.get("scenes"), music_path or request.get("music_filename"), request.get("visual_mode", "auto"), request.get("music_volume", 0.12), scene_paths, logo_path, request.get("brand_logo_asset_id"), request.get("music_asset_id"), progress_callback)
            item = db.get(Workflow, workflow_id)
            item.config = {**(item.config or {}), "video_render": {**(item.config or {})["video_render"], "status": "ready_for_review", "url": url, "progress": {"stage": "complete", "percent": 100, "message": "Video render completed and validated"}}}
            db.commit()
            return {"workflow_id": workflow_id, "status": "ready_for_review", "url": url}
        except Exception as exc:
            logger.exception("Video render failed (workflow_id=%s, render_id=%s)", workflow_id, render_id)
            item = db.get(Workflow, workflow_id)
            item.config = {**(item.config or {}), "video_render": {**(item.config or {})["video_render"], "status": "retrying" if self.request.retries < self.max_retries else "failed", "error": str(exc)[:1200], "progress": {"stage": "failed", "percent": 0, "message": "Render failed; inspect the error details and worker logs."}}}
            db.commit()
            raise
    finally:
        db.close()
