from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.workflow import Workflow
from app.schemas.workflow import WorkflowCreate
from app.worker.tasks import execute_workflow
router=APIRouter()
def serialize(x): return {'id':x.id,'topic':x.topic,'status':x.status,'config':x.config,'created_at':x.created_at.isoformat()}
@router.post('/workflows',status_code=201,tags=['workflows'])
def create_workflow(payload:WorkflowCreate,db:Session=Depends(get_db)):
 x=Workflow(topic=payload.topic,config=payload.config,status='draft'); db.add(x); db.commit(); db.refresh(x); return serialize(x)
@router.get('/workflows/{workflow_id}',tags=['workflows'])
def get_workflow(workflow_id:str,db:Session=Depends(get_db)):
 x=db.get(Workflow,workflow_id)
 if not x: raise HTTPException(404,'Workflow not found')
 return serialize(x)
@router.post('/workflows/{workflow_id}/queue',tags=['workflows'])
def queue_workflow(workflow_id:str,db:Session=Depends(get_db)):
 x=db.get(Workflow,workflow_id)
 if not x: raise HTTPException(404,'Workflow not found')
 if x.status not in {'draft','failed'}: raise HTTPException(409,f'Cannot queue workflow in {x.status} state')
 x.status='queued'; db.commit(); execute_workflow.delay(workflow_id)
 return {'id':x.id,'status':x.status,'message':'Queued for agent execution; external publishing is disabled.'}
