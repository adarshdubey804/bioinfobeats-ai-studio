"""ElevenLabs TTS + FFmpeg rendering for a simple branded first-cut video."""
from __future__ import annotations
import os
import re
import subprocess
from pathlib import Path
from typing import Literal
import httpx
from app.core.config import settings

class RenderConfigurationError(RuntimeError):
    pass

def _safe_id(value: str) -> str:
    if not re.fullmatch(r"[a-f0-9-]{8,64}", value):
        raise ValueError("Invalid render identifier")
    return value

def build_srt(script: str, output: Path, words_per_minute: int = 145) -> None:
    """Create readable sentence-level captions with estimated timings."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script.strip()) if s.strip()]
    cursor = 0.0
    lines = []
    for index, sentence in enumerate(sentences, 1):
        duration = max(2.0, len(sentence.split()) / words_per_minute * 60)
        start, end = cursor, cursor + duration
        def stamp(seconds: float) -> str:
            ms = int(seconds * 1000)
            h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); sec, ms = divmod(ms, 1000)
            return f"{h:02}:{m:02}:{sec:02},{ms:03}"
        lines.extend([str(index), f"{stamp(start)} --> {stamp(end)}", sentence, ""])
        cursor = end
    output.write_text("\n".join(lines), encoding="utf-8")

def render_video(render_id: str, title: str, script: str, aspect: Literal["vertical", "landscape"]) -> str:
    if not settings.elevenlabs_api_key or not settings.elevenlabs_voice_id:
        raise RenderConfigurationError("Configure ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID to render narration.")
    render_id = _safe_id(render_id)
    root = Path(settings.media_storage_dir).resolve()
    job_dir = (root / render_id).resolve()
    if root not in job_dir.parents:
        raise ValueError("Invalid output directory")
    job_dir.mkdir(parents=True, exist_ok=True)
    audio_path, srt_path, video_path = job_dir / "narration.mp3", job_dir / "captions.srt", job_dir / "final.mp4"
    response = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}",
        headers={"xi-api-key": settings.elevenlabs_api_key, "Accept": "audio/mpeg", "Content-Type": "application/json"},
        json={"text": script, "model_id": settings.elevenlabs_model_id},
        timeout=settings.render_timeout_seconds,
    )
    response.raise_for_status()
    audio_path.write_bytes(response.content)
    build_srt(script, srt_path)
    width, height = (1080, 1920) if aspect == "vertical" else (1920, 1080)
    escaped_title = title.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    # A dependable first-cut template: branded title slate, generated narration and timed captions.
    vf = (
        f"drawtext=text='{escaped_title}':fontcolor=white:fontsize=48:"
        f"x=(w-text_w)/2:y=h*0.18:box=1:boxcolor=0x102A43@0.8:boxborderw=24,"
        f"subtitles={srt_path.as_posix()}"
    )
    command = [
        settings.ffmpeg_binary, "-y", "-f", "lavfi", "-i",
        f"color=c=0x071A2B:s={width}x{height}:r=30", "-i", str(audio_path),
        "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(video_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=settings.render_timeout_seconds * 4)
    return f"/media/{render_id}/final.mp4"
