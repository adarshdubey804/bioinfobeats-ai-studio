from pathlib import Path
from uuid import uuid4
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User

router = APIRouter(prefix="/audio", tags=["audio-studio"])


def _credentials():
    if not settings.elevenlabs_api_key:
        raise HTTPException(503, "Configure ELEVENLABS_API_KEY to use the voice library.")


@router.get("/voices")
def list_voices(user: User = Depends(get_current_user)):
    _credentials()
    try:
        response = httpx.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": settings.elevenlabs_api_key},
            timeout=settings.render_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, "ElevenLabs could not return the voice library.") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "Unable to reach the ElevenLabs voice library.") from exc
    voices = []
    for voice in payload.get("voices", []):
        labels = voice.get("labels") or {}
        voices.append({
            "voice_id": voice.get("voice_id"),
            "name": voice.get("name") or "Unnamed voice",
            "category": voice.get("category") or "custom",
            "description": voice.get("description") or "",
            "labels": {key: labels[key] for key in ("accent", "age", "gender", "use_case") if labels.get(key)},
        })
    return {"voices": voices, "default_voice_id": settings.elevenlabs_voice_id or None}


class VoicePreviewRequest(BaseModel):
    text: str = Field(min_length=10, max_length=800)
    voice_id: str = Field(min_length=1, max_length=100)
    stability: float = Field(default=0.48, ge=0, le=1)
    similarity: float = Field(default=0.78, ge=0, le=1)
    speed: float = Field(default=1.0, ge=0.7, le=1.2)


@router.post("/voice-preview")
def create_voice_preview(payload: VoicePreviewRequest, user: User = Depends(get_current_user)):
    _credentials()
    try:
        response = httpx.post(
            "https://api.elevenlabs.io/v1/text-to-speech/" + payload.voice_id,
            headers={"xi-api-key": settings.elevenlabs_api_key, "Accept": "audio/mpeg", "Content-Type": "application/json"},
            json={
                "text": payload.text,
                "model_id": settings.elevenlabs_model_id,
                "voice_settings": {"stability": payload.stability, "similarity_boost": payload.similarity, "speed": payload.speed},
            },
            timeout=settings.render_timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, "ElevenLabs rejected the voice preview request. Check the voice ID and account access.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Unable to generate the voice preview.") from exc
    if not response.content or not (response.content.startswith(b"ID3") or (len(response.content) > 1 and response.content[0] == 0xFF and response.content[1] & 0xE0 == 0xE0)):
        raise HTTPException(502, "ElevenLabs returned an invalid audio preview.")
    filename = uuid4().hex + ".mp3"
    root = Path(settings.media_storage_dir).resolve()
    folder = (root / "voice_previews" / str(user.id)).resolve()
    if root not in folder.parents:
        raise HTTPException(400, "Invalid preview storage path.")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / filename).write_bytes(response.content)
    return {"url": f"/media/voice_previews/{user.id}/{filename}", "size_bytes": len(response.content)}
