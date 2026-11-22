from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.workflow import Workflow
from app.schemas.workflow import WorkflowCreate
from app.worker.tasks import execute_workflow

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
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)):
    item = Workflow(topic=payload.topic, config=payload.config, status='draft')
    db.add(item); db.commit(); db.refresh(item)
    return serialize(item)

@router.get('/workflows/{workflow_id}', tags=['workflows'])
def get_workflow(workflow_id: str, db: Session = Depends(get_db)):
    item = db.get(Workflow, workflow_id)
    if not item: raise HTTPException(404, 'Workflow not found')
    return serialize(item)

@router.post('/workflows/{workflow_id}/queue', tags=['workflows'])
def queue_workflow(workflow_id: str, db: Session = Depends(get_db)):
    item = db.get(Workflow, workflow_id)
    if not item: raise HTTPException(404, 'Workflow not found')
    if item.status not in {'draft', 'failed'}: raise HTTPException(409, f'Cannot queue workflow in {item.status} state')
    item.status = 'queued'; db.commit()
    execute_workflow.delay(workflow_id)
    return {'id': item.id, 'status': item.status, 'message': 'Queued for six-agent generation. Review is required; nothing is published.'}
