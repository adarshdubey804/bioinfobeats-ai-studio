from fastapi import APIRouter,Depends,HTTPException,status
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
from pydantic import ValidationError
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest,LoginRequest,TokenResponse
from app.core.security import hash_password,verify_password,create_access_token,ALGORITHM
from app.core.config import settings
router=APIRouter();bearer=HTTPBearer(auto_error=False)
@router.post('/auth/register',status_code=201,tags=['auth'])
def register(payload:RegisterRequest,db:Session=Depends(get_db)):
 email=str(payload.email).lower()
 if db.query(User).filter(User.email==email).first():raise HTTPException(409,'Email already registered')
 user=User(email=email,password_hash=hash_password(payload.password));db.add(user);db.commit();db.refresh(user)
 return {'id':user.id,'email':user.email,'created_at':user.created_at.isoformat()}
@router.post('/auth/login',response_model=TokenResponse,tags=['auth'])
def login(payload:LoginRequest,db:Session=Depends(get_db)):
 user=db.query(User).filter(User.email==str(payload.email).lower()).first()
 if not user or not user.is_active or not verify_password(payload.password,user.password_hash):raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='Invalid email or password',headers={'WWW-Authenticate':'Bearer'})
 return TokenResponse(access_token=create_access_token(user.id))
@router.get('/auth/me',tags=['auth'])
def me(credentials:HTTPAuthorizationCredentials|None=Depends(bearer),db:Session=Depends(get_db)):
 if not credentials:raise HTTPException(401,'Bearer token required')
 try:subject=jwt.decode(credentials.credentials,settings.secret_key,algorithms=[ALGORITHM]).get('sub')
 except jwt.PyJWTError:raise HTTPException(401,'Invalid or expired token')
 user=db.get(User,subject) if subject else None
 if not user or not user.is_active:raise HTTPException(401,'User not found or inactive')
 return {'id':user.id,'email':user.email}
