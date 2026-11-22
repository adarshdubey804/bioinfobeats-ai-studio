"""Resumable one-click production assembly with progress and bounded retries."""
import logging
from app.worker.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.workflow import Workflow
from app.rendering.service import render_video
from app.worker.video_tasks import _prepare_assets
from app.creative.service import create_creative_package

logger = logging.getLogger(__name__)


def _persist_progress(workflow_id: str, render_id: str, progress: dict) -> None:
    session = SessionLocal()
    try:
        item = session.get(Workflow, workflow_id)
        if item is None:
            return
        config = item.config or {}
        assembly = config.get("production_assembly") or {}
        if assembly.get("render_id") != render_id:
            return
        current = config.get("video_render") or {}
        item.config = {
            **config,
            "video_render": {**current, "id": render_id, "status": "rendering", "progress": progress},
            "production_assembly": {**assembly, "status": "rendering", "step": progress.get("stage", "rendering"), "progress": progress},
        }
        session.commit()
    finally:
        session.close()


@celery_app.task(
    name="app.worker.production_tasks.assemble_approved_production",
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def assemble_approved_production(self, workflow_id: str, render_id: str):
    db = SessionLocal()
    try:
        item = db.get(Workflow, workflow_id)
        if item is None:
            return {"status": "not_found"}
        config = item.config or {}
        job = config.get("production_assembly") or {}
        if job.get("render_id") != render_id:
            return {"status": "superseded"}
        script = config.get("approved_script") or ""
        title = config.get("approved_title") or item.topic
        if len(script.strip()) < 30:
            job = {**job, "status": "failed", "error": "Approved script is missing or too short."}
            item.config = {**config, "production_assembly": job}
            db.commit()
            return {"status": "failed", "error": job["error"]}

        render_record = config.get("video_render") or {}
        video_url = render_record.get("url") if render_record.get("status") == "ready_for_review" else None
        if not video_url:
            job = {**job, "status": "rendering", "step": "narration_and_video", "attempt": self.request.retries + 1}
            item.config = {
                **config,
                "production_assembly": job,
                "video_render": {"id": render_id, "status": "rendering", "title": title, "aspect": job["aspect"]},
            }
            db.commit()
            options = config.get("video_render_request") or {}
            scene_paths, music_path, logo_path = _prepare_assets(db, item.owner_id, render_id, options)
            progress = lambda value: _persist_progress(workflow_id, render_id, value)
            video_url = render_video(
                render_id,
                title,
                script,
                job["aspect"],
                options.get("scenes") or [],
                music_path,
                job.get("visual_mode", "auto"),
                options.get("music_volume", 0.12),
                scene_paths,
                logo_path,
                options.get("brand_logo_asset_id"),
                options.get("music_asset_id"),
                progress,
                voice_id=options.get("voice_id"),
                voice_stability=options.get("voice_stability", 0.48),
                voice_similarity=options.get("voice_similarity", 0.78),
                voice_speed=options.get("voice_speed", 1.0),
                pronunciation_dictionary=options.get("pronunciation_dictionary", ""),
            )
            item = db.get(Workflow, workflow_id)
            config = item.config or {}
            item.config = {
                **config,
                "video_render": {
                    "id": render_id,
                    "status": "ready_for_review",
                    "title": title,
                    "aspect": job["aspect"],
                    "storyboard": "auto",
                    "url": video_url,
                    "progress": {"stage": "complete", "percent": 100, "message": "Video render completed and validated"},
                },
                "production_assembly": {**job, "status": "generating_creatives", "step": "thumbnails_and_social_copy", "video_url": video_url},
            }
            db.commit()

        item = db.get(Workflow, workflow_id)
        config = item.config or {}
        current_job = config.get("production_assembly") or job
        item.config = {**config, "production_assembly": {**current_job, "status": "generating_creatives", "step": "thumbnails_and_social_copy", "video_url": video_url}}
        db.commit()
        creative = create_creative_package(workflow_id, item.topic, title, script, ["YouTube", "Instagram", "LinkedIn"])
        item = db.get(Workflow, workflow_id)
        config = item.config or {}
        item.config = {
            **config,
            "creative_package": creative,
            "production_assembly": {**(config.get("production_assembly") or job), "status": "ready_for_review", "step": "complete", "video_url": video_url, "progress": {"stage": "complete", "percent": 100, "message": "Video and creative assets are ready for review"}},
        }
        db.commit()
        return {"workflow_id": workflow_id, "status": "ready_for_review", "video_url": video_url}
    except Exception as exc:
        logger.exception("Production assembly failed (workflow_id=%s, render_id=%s)", workflow_id, render_id)
        item = db.get(Workflow, workflow_id)
        if item is not None:
            config = item.config or {}
            prior = config.get("production_assembly") or {}
            retrying = self.request.retries < self.max_retries
            item.config = {
                **config,
                "production_assembly": {
                    **prior,
                    "status": "retrying" if retrying else "failed",
                    "step": prior.get("step", "failed"),
                    "attempt": self.request.retries + 1,
                    "error": str(exc)[:1200],
                },
            }
            db.commit()
        raise
    finally:
        db.close()
