from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.workflow import Workflow
from app.models.user import User
from app.models.job_run import JobRun
import uuid
from app.schemas.workflow import WorkflowCreate
from app.worker.tasks import execute_workflow
from app.api.deps import get_current_user, get_owned_workflow
from app.worker.celery_app import celery_app
from datetime import datetime, timezone
from app.worker.job_health import job_health

router = APIRouter()

def serialize(item: Workflow):
    config = item.config or {}
    return {
        'id': item.id, 'topic': item.topic, 'status': item.status,
        'config': {k: v for k, v in config.items() if k != 'agent_outputs'},
        'agent_outputs': config.get('agent_outputs'),
        'pipeline_error': config.get('pipeline_error'),
        'created_at': item.created_at.isoformat(),
    }

@router.post('/workflows', status_code=201, tags=['workflows'])
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = Workflow(owner_id=user.id, topic=payload.topic, config=payload.config, status='draft')
    db.add(item); db.commit(); db.refresh(item)
    return serialize(item)

@router.get('/workflows', tags=['workflows'])
def list_workflows(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [serialize(item) for item in db.query(Workflow).filter(Workflow.owner_id == user.id).order_by(Workflow.created_at.desc()).limit(100).all()]

@router.get('/workflows/{workflow_id}', tags=['workflows'])
def get_workflow(workflow_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return serialize(get_owned_workflow(workflow_id, user, db))

@router.post('/workflows/{workflow_id}/queue', tags=['workflows'])
def queue_workflow(workflow_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = get_owned_workflow(workflow_id, user, db)
    if item.status not in {'draft', 'failed', 'cancelled'}: raise HTTPException(409, f'Cannot queue workflow in {item.status} state')
    item.status = 'queued'; db.commit()
    run = JobRun(id=str(uuid.uuid4()), workflow_id=item.id, task_type="agent_pipeline", status="queued", progress={"stage": "queued", "percent": 0})
    db.add(run); db.commit(); db.refresh(run)
    result = execute_workflow.delay(workflow_id, run.id)
    run.celery_task_id = result.id
    db.commit()
    return {'id': item.id, 'status': item.status, 'job_id': run.id, 'message': 'Queued for six-agent generation.'}

@router.get('/workflows/{workflow_id}/jobs', tags=['workflows'])
def list_workflow_jobs(workflow_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_owned_workflow(workflow_id, user, db)
    runs = db.query(JobRun).filter(JobRun.workflow_id == workflow_id).order_by(JobRun.created_at.desc()).limit(50).all()
    return [{"id": r.id, "task_type": r.task_type, "celery_task_id": r.celery_task_id, "status": r.status, "progress": r.progress, "error": r.error, "cancel_requested": r.cancel_requested, "attempts": r.attempts, "created_at": r.created_at.isoformat(), "started_at": r.started_at.isoformat() if r.started_at else None, "finished_at": r.finished_at.isoformat() if r.finished_at else None, **job_health(r)} for r in runs]


@router.post('/workflows/{workflow_id}/jobs/{job_id}/cancel', tags=['workflows'])
def cancel_workflow_job(workflow_id: str, job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = get_owned_workflow(workflow_id, user, db)
    run = db.query(JobRun).filter(JobRun.id == job_id, JobRun.workflow_id == workflow_id).first()
    if run is None:
        raise HTTPException(404, 'Job not found')
    if run.status in {'succeeded', 'failed', 'cancelled'}:
        raise HTTPException(409, f'Cannot cancel a job in {run.status} state')
    run.cancel_requested = True
    if run.status == 'queued':
        run.status = 'cancelled'
        run.finished_at = datetime.now(timezone.utc)
        run.progress = {'stage': 'cancelled', 'percent': 0, 'message': 'Cancelled before execution'}
        if run.celery_task_id:
            celery_app.control.revoke(run.celery_task_id, terminate=False)
        if run.task_type == 'agent_pipeline':
            item.status = 'cancelled'
        elif run.task_type == 'production_assembly':
            config = item.config or {}
            assembly = config.get('production_assembly') or {}
            item.config = {**config, 'production_assembly': {**assembly, 'status': 'cancelled', 'step': 'cancelled'}}
    else:
        run.status = 'cancelling'
        run.progress = {**(run.progress or {}), 'message': 'Cancellation requested; worker will stop at its next safe checkpoint'}
        if run.celery_task_id:
            celery_app.control.revoke(run.celery_task_id, terminate=False)
    db.commit()
    return {'job_id': run.id, 'status': run.status, 'cancel_requested': True, 'message': 'Cancellation recorded'}
