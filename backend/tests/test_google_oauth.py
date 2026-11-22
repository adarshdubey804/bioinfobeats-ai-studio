import pytest
from fastapi import HTTPException
from app.oauth.google import encrypt_refresh_token, decrypt_refresh_token
from app.core.config import settings

def test_refresh_token_encryption_round_trip(monkeypatch):
    monkeypatch.setattr(settings, "oauth_token_encryption_key", "test-encryption-secret")
    value = encrypt_refresh_token("refresh-token-example")
    assert value != "refresh-token-example"
    assert decrypt_refresh_token(value) == "refresh-token-example"

def test_encryption_rejects_default_secret(monkeypatch):
    monkeypatch.setattr(settings, "oauth_token_encryption_key", "")
    monkeypatch.setattr(settings, "secret_key", "unsafe-development-key-change-me")
    with pytest.raises(HTTPException):
        encrypt_refresh_token("refresh-token-example")
