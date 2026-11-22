from app.worker.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.workflow import Workflow
from app.creative.service import create_creative_package

@celery_app.task(name="app.worker.creative_tasks.generate_workflow_creatives", bind=True, max_retries=0)
def generate_workflow_creatives(self, workflow_id: str):
    db = SessionLocal()
    try:
        item = db.get(Workflow, workflow_id)
        if not item:
            return {"status": "not_found"}
        config = item.config or {}
        request = config.get("creative_request")
        if not request:
            return {"status": "missing_request"}
        item.config = {**config, "creative_package": {"status": "generating", "title": request["title"]}}
        db.commit()
        try:
            package = create_creative_package(workflow_id, item.topic, request["title"], request["script"], request["platforms"])
            item.config = {**(item.config or {}), "creative_package": package}
            db.commit()
            return {"workflow_id": workflow_id, "status": "ready_for_review"}
        except Exception as exc:
            item.config = {**(item.config or {}), "creative_package": {"status": "failed", "error": str(exc)[:1000]}}
            db.commit()
            raise
    finally:
        db.close()
