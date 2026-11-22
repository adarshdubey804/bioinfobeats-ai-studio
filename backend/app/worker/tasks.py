from datetime import datetime, timezone
from app.worker.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.workflow import Workflow
from app.models.job_run import JobRun
from app.agents.pipeline import run_pipeline

@celery_app.task(name='app.worker.tasks.execute_workflow', bind=True, max_retries=2)
def execute_workflow(self, workflow_id: str, job_id: str | None = None):
    db = SessionLocal()
    try:
        item = db.get(Workflow, workflow_id)
        run = db.get(JobRun, job_id) if job_id else None
        if not item:
            if run:
                run.status = "failed"
                run.error = "Workflow not found."
                run.finished_at = datetime.now(timezone.utc)
                db.commit()
            return {"status": "not_found"}
        if run and run.cancel_requested:
            run.status = 'cancelled'
            run.finished_at = datetime.now(timezone.utc)
            run.progress = {'stage': 'cancelled', 'percent': 0, 'message': 'Cancelled before execution'}
            item.status = 'cancelled'
            db.commit()
            return {'workflow_id': workflow_id, 'status': 'cancelled'}
        if run:
            run.celery_task_id = self.request.id
            run.status = "running"
            run.started_at = run.started_at or datetime.now(timezone.utc)
            run.attempts += 1
            run.progress = {"stage": "agent_pipeline", "percent": 5, "message": "Six-agent pipeline started"}
        item.status = "running"
        db.commit()
        try:
            outputs = run_pipeline(item.topic, item.config or {})
            if run:
                db.refresh(run)
            if run and run.cancel_requested:
                run.status = 'cancelled'
                run.finished_at = datetime.now(timezone.utc)
                run.progress = {'stage': 'cancelled', 'percent': 0, 'message': 'Cancellation acknowledged after pipeline completion'}
                item.status = 'cancelled'
                db.commit()
                return {'workflow_id': workflow_id, 'status': 'cancelled'}
            item.config = {**(item.config or {}), "agent_outputs": outputs, "pipeline_version": "phase-2"}
            item.status = "ready_for_review"
            if run:
                run.status = "succeeded"
                run.progress = {"stage": "complete", "percent": 100, "message": "All pipeline agents completed"}
                run.finished_at = datetime.now(timezone.utc)
                run.error = None
            db.commit()
            return {"workflow_id": workflow_id, "status": item.status, "agents_completed": list(outputs.keys())}
        except Exception as exc:
            item.config = {**(item.config or {}), "pipeline_error": str(exc)}
            item.status = "failed"
            if run:
                run.status = "failed"
                run.error = str(exc)[:4000]
                run.progress = {"stage": "failed", "percent": 0, "message": "Pipeline failed"}
                run.finished_at = datetime.now(timezone.utc)
            db.commit()
            raise
    finally:
        db.close()
