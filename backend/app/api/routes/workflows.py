from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.workflow import Workflow
from app.models.user import User
from app.schemas.workflow import WorkflowCreate
from app.worker.tasks import execute_workflow
from app.api.deps import get_current_user, get_owned_workflow

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
    if item.status not in {'draft', 'failed'}: raise HTTPException(409, f'Cannot queue workflow in {item.status} state')
    item.status = 'queued'; db.commit()
    execute_workflow.delay(workflow_id)
    return {'id': item.id, 'status': item.status, 'message': 'Queued for six-agent generation. Review is required; nothing is published.'}
