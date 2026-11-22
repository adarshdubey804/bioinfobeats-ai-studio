from fastapi import APIRouter
from app.agents.registry import AGENTS
router=APIRouter()
@router.get('/agents',tags=['agents'])
def list_agents(): return [{'key':a.key,'name':a.name,'purpose':a.purpose,'inputs':list(a.inputs),'outputs':list(a.outputs)} for a in AGENTS]
