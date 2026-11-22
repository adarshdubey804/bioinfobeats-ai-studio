from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import jwt
import httpx
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.session import get_db
from app.models.user import User
from app.models.google_oauth import GoogleOAuthConnection
from app.oauth.google import SCOPES, exchange_code, encrypt_refresh_token, revoke_token, decrypt_refresh_token

router = APIRouter()

@router.get("/oauth/google/start", tags=["oauth"])
def google_oauth_start(user: User = Depends(get_current_user)):
    if not settings.google_oauth_client_id:
        raise HTTPException(503, "Google OAuth client ID is not configured.")
    state = jwt.encode({"sub": user.id, "purpose": "google_youtube_connect", "exp": datetime.now(timezone.utc) + timedelta(minutes=10)}, settings.secret_key, algorithm=ALGORITHM)
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return {"authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)}

@router.get("/oauth/google/callback", tags=["oauth"])
def google_oauth_callback(code: str, state: str, error: str | None = None, db: Session = Depends(get_db)):
    if error:
        return RedirectResponse(settings.google_oauth_frontend_url + "/?google_oauth=denied")
    try:
        payload = jwt.decode(state, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("purpose") != "google_youtube_connect" or not payload.get("sub"):
            raise ValueError("Invalid OAuth state")
        user = db.get(User, payload["sub"])
        if user is None or not user.is_active:
            raise ValueError("Account no longer exists")
        tokens = exchange_code(code)
        encrypted = encrypt_refresh_token(tokens["refresh_token"])
        connection = db.query(GoogleOAuthConnection).filter_by(user_id=user.id).first()
        if connection:
            connection.refresh_token_encrypted = encrypted
            connection.scopes = " ".join(tokens.get("scope", SCOPES[0]).split())
            connection.updated_at = datetime.now(timezone.utc)
        else:
            db.add(GoogleOAuthConnection(user_id=user.id, refresh_token_encrypted=encrypted, scopes=" ".join(tokens.get("scope", SCOPES[0]).split())))
        db.commit()
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(400, "Invalid or expired Google OAuth state.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Google token exchange failed.") from exc
    return RedirectResponse(settings.google_oauth_frontend_url + "/?google_oauth=connected")

@router.get("/oauth/google/status", tags=["oauth"])
def google_oauth_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    connection = db.query(GoogleOAuthConnection).filter_by(user_id=user.id).first()
    return {"connected": connection is not None, "scopes": connection.scopes if connection else [], "connected_at": connection.connected_at.isoformat() if connection else None}

@router.delete("/oauth/google", tags=["oauth"])
def google_oauth_disconnect(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    connection = db.query(GoogleOAuthConnection).filter_by(user_id=user.id).first()
    if not connection:
        return {"connected": False}
    try:
        revoke_token(decrypt_refresh_token(connection.refresh_token_encrypted))
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Google token revocation failed; connection record was retained.") from exc
    db.delete(connection)
    db.commit()
    return {"connected": False, "message": "Google connection revoked and removed."}
