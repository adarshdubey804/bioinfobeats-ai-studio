"""Google OAuth code flow and encrypted refresh-token storage."""
import base64
import hashlib
from cryptography.fernet import Fernet
from fastapi import HTTPException
import httpx
from app.core.config import settings

SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly"]

def _fernet() -> Fernet:
    secret = settings.oauth_token_encryption_key or settings.secret_key
    if not secret or secret == "unsafe-development-key-change-me":
        raise HTTPException(503, "Set a strong OAUTH_TOKEN_ENCRYPTION_KEY before connecting Google.")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)

def encrypt_refresh_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()

def decrypt_refresh_token(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()

def exchange_code(code: str) -> dict:
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(503, "Google OAuth client credentials are not configured.")
    response = httpx.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": settings.google_oauth_client_id,
        "client_secret": settings.google_oauth_client_secret,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "grant_type": "authorization_code",
    }, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("refresh_token"):
        raise HTTPException(400, "Google did not return a refresh token. Revoke the app grant and reconnect with consent.")
    return payload

def refresh_access_token(refresh_token: str) -> dict:
    response = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": settings.google_oauth_client_id,
        "client_secret": settings.google_oauth_client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, timeout=30)
    response.raise_for_status()
    return response.json()

def revoke_token(refresh_token: str) -> None:
    response = httpx.post("https://oauth2.googleapis.com/revoke", params={"token": refresh_token}, timeout=30)
    response.raise_for_status()
