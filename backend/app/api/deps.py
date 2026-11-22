from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.session import get_db
from app.models.user import User

bearer = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if credentials is None:
        raise HTTPException(401, "Bearer token required")
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[ALGORITHM])
        subject = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, subject) if subject else None
    if user is None or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    return user

def get_owned_workflow(workflow_id: str, user: User, db: Session):
    from app.models.workflow import Workflow
    item = db.get(Workflow, workflow_id)
    if item is None or item.owner_id != user.id:
        raise HTTPException(404, "Workflow not found")
    return item
