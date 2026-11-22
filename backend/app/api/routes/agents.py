from fastapi import APIRouter, Depends
from app.agents.registry import AGENTS
from app.api.deps import get_current_user
router=APIRouter()
@router.get('/agents',tags=['agents'],dependencies=[Depends(get_current_user)])
def list_agents(): return [{'key':a.key,'name':a.name,'purpose':a.purpose,'inputs':list(a.inputs),'outputs':list(a.outputs)} for a in AGENTS]
