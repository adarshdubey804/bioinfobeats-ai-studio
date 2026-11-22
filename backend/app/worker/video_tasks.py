from app.worker.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.workflow import Workflow
from app.rendering.service import render_video

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
            url = render_video(render_id, request["title"], request["script"], request["aspect"], request.get("scenes"), request.get("music_filename"), request.get("visual_mode", "auto"), request.get("music_volume", 0.12))
            item.config = {**(item.config or {}), "video_render": {**(item.config or {})["video_render"], "status": "ready_for_review", "url": url}}
            db.commit()
            return {"workflow_id": workflow_id, "status": "ready_for_review", "url": url}
        except Exception as exc:
            item.config = {**(item.config or {}), "video_render": {**(item.config or {})["video_render"], "status": "retrying" if self.request.retries < self.max_retries else "failed", "error": str(exc)[:1000]}}
            db.commit()
            raise
    finally:
        db.close()
