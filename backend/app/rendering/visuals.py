"""Generate scene artwork using the OpenAI Images API."""
import base64
from pathlib import Path
import httpx
from app.core.config import settings

class ImageProviderError(RuntimeError):
    pass

def generate_scene_image(prompt: str, output: Path, aspect: str) -> None:
    if not settings.openai_api_key:
        raise ImageProviderError("OPENAI_API_KEY is required for AI scene images.")
    size = "1024x1536" if aspect == "vertical" else "1536x1024"
    response = httpx.post(
        f"{settings.openai_base_url.rstrip('/')}/images/generations",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json={"model": settings.openai_image_model, "prompt": prompt, "size": size, "quality": "medium", "n": 1},
        timeout=settings.render_timeout_seconds * 2,
    )
    response.raise_for_status()
    payload = response.json()
    encoded = payload.get("data", [{}])[0].get("b64_json")
    if not encoded:
        raise ImageProviderError("Image provider response did not contain b64_json image data.")
    output.write_bytes(base64.b64decode(encoded))
