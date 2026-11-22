"""Narration, generated scene artwork, subtitles and FFmpeg assembly."""
from __future__ import annotations
import re
import subprocess
from pathlib import Path
from typing import Literal
import httpx
from app.core.config import settings
from app.rendering.visuals import generate_scene_image

class RenderConfigurationError(RuntimeError):
    pass

def _safe_id(value: str) -> str:
    if not re.fullmatch(r"[a-f0-9-]{8,64}", value):
        raise ValueError("Invalid render identifier")
    return value

def build_srt(script: str, output: Path, words_per_minute: int = 145) -> None:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\\s+", script.strip()) if s.strip()]
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
    output.write_text("\\n".join(lines), encoding="utf-8")

def _run(command: list[str], timeout: int | None = None) -> None:
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout or settings.render_timeout_seconds * 4)

def render_video(render_id: str, title: str, script: str, aspect: Literal["vertical", "landscape"], scenes: list[dict] | None = None, music_filename: str | None = None) -> str:
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
    scene_items = scenes or []
    if scene_items:
        if len(scene_items) > 8:
            raise ValueError("A maximum of 8 generated scenes is supported per render.")
        segment_paths = []
        for index, scene in enumerate(scene_items):
            image_path = job_dir / f"scene-{index + 1:02}.png"
            prompt = (
                "Create a polished, cinematic educational science video still. "
                "No text, no labels, no logos, no watermark. Strong visual hierarchy, "
                "accurate scientific imagery, deep navy and electric cyan BioinfoBeats palette. "
                + scene["prompt"]
            )
            generate_scene_image(prompt, image_path, aspect)
            segment_path = job_dir / f"segment-{index + 1:02}.mp4"
            duration = max(3, min(int(scene.get("duration_seconds", 6)), 20))
            _run([
                settings.ffmpeg_binary, "-y", "-loop", "1", "-i", str(image_path), "-t", str(duration),
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},zoompan=z='min(zoom+0.0008,1.08)':d=1:s={width}x{height}:fps=30,format=yuv420p,fade=t=in:st=0:d=0.35,fade=t=out:st={max(0,duration-0.35)}:d=0.35",
                "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-an", str(segment_path),
            ])
            segment_paths.append(segment_path)
        concat_file = job_dir / "scenes.txt"
        concat_file.write_text("".join(f"file '{p.name}'\\n" for p in segment_paths), encoding="utf-8")
        visual_path = job_dir / "visuals.mp4"
        _run([settings.ffmpeg_binary, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(visual_path)])
        visual_input = str(visual_path)
        vf = f"subtitles={srt_path.as_posix()}"
    else:
        visual_input = None
        escaped_title = title.replace("\\\\", "\\\\\\\\").replace(":", "\\\\:").replace("'", "\\\\'")
        vf = (
            f"drawtext=text='{escaped_title}':fontcolor=white:fontsize=48:"
            f"x=(w-text_w)/2:y=h*0.18:box=1:boxcolor=0x102A43@0.8:boxborderw=24,"
            f"subtitles={srt_path.as_posix()}"
        )
    music_path = None
    if music_filename:
        if Path(music_filename).name != music_filename or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", music_filename):
            raise ValueError("Music filename must be a simple filename stored in the render job folder.")
        music_path = job_dir / music_filename
        if not music_path.is_file():
            raise ValueError("Requested music file was not found in this render's media folder.")
    if visual_input:
        command = [settings.ffmpeg_binary, "-y", "-i", visual_input, "-i", str(audio_path)]
    else:
        command = [settings.ffmpeg_binary, "-y", "-f", "lavfi", "-i", f"color=c=0x071A2B:s={width}x{height}:r=30", "-i", str(audio_path)]
    if music_path:
        command += ["-stream_loop", "-1", "-i", str(music_path)]
        command += ["-vf", vf, "-filter_complex", "[1:a]volume=1.0[voice];[2:a]volume=0.12[music];[voice][music]amix=inputs=2:duration=first:dropout_transition=2[aout]", "-map", "0:v", "-map", "[aout]"]
    else:
        command += ["-vf", vf, "-map", "0:v", "-map", "1:a"]
    command += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(video_path)]
    _run(command)
    return f"/media/{render_id}/final.mp4"
