from app.worker.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.workflow import Workflow
from app.agents.pipeline import run_pipeline

@celery_app.task(name='app.worker.tasks.execute_workflow', bind=True, max_retries=2)
def execute_workflow(self, workflow_id: str):
    db = SessionLocal()
    try:
        item = db.get(Workflow, workflow_id)
        if not item:
            return {'status': 'not_found'}
        item.status = 'running'
        db.commit()
        try:
            outputs = run_pipeline(item.topic, item.config or {})
            item.config = {**(item.config or {}), 'agent_outputs': outputs, 'pipeline_version': 'phase-2'}
            item.status = 'ready_for_review'
            db.commit()
            return {'workflow_id': workflow_id, 'status': item.status, 'agents_completed': list(outputs.keys())}
        except Exception as exc:
            item.config = {**(item.config or {}), 'pipeline_error': str(exc)}
            item.status = 'failed'
            db.commit()
            raise
    finally:
        db.close()
