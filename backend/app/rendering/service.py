"""Narration, timed scene animation, captions and FFmpeg assembly."""
from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path
from typing import Literal
import httpx
from app.core.config import settings
from app.rendering.visuals import generate_scene_image
from app.rendering.storyboard import build_storyboard
from app.rendering.motion import generate_motion_clip, MotionProviderError

class RenderConfigurationError(RuntimeError):
    pass

def _safe_id(value: str) -> str:
    if not re.fullmatch(r"[a-f0-9-]{8,64}", value):
        raise ValueError("Invalid render identifier")
    return value

def _run(command: list[str], timeout: int | None = None) -> str:
    result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout or settings.render_timeout_seconds * 4)
    return result.stdout.strip()

def _duration(path: Path) -> float:
    value = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    duration = float(value)
    if duration <= 0:
        raise ValueError("Could not determine narration duration.")
    return duration

def _stamp(seconds: float) -> str:
    ms = int(seconds * 1000)
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); sec, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{sec:02},{ms:03}"

def build_srt(script: str, output: Path, duration_seconds: float | None = None, words_per_minute: int = 145) -> None:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script.strip()) if s.strip()]
    if not sentences:
        raise ValueError("Narration script is empty.")
    weights = [max(1, len(sentence.split())) for sentence in sentences]
    total = sum(weights)
    duration = duration_seconds or total / words_per_minute * 60
    cursor = 0.0
    lines = []
    for index, (sentence, weight) in enumerate(zip(sentences, weights), 1):
        end = duration if index == len(sentences) else cursor + duration * weight / total
        words = sentence.split()
        chunks = [" ".join(words[i:i+10]) for i in range(0, len(words), 10)]
        caption = "\\N".join(chunks)
        lines.extend([str(index), f"{_stamp(cursor)} --> {_stamp(end)}", caption, ""])
        cursor = end
    output.write_text("\n".join(lines), encoding="utf-8")

def _scene_durations(scenes: list[dict], script: str, duration: float) -> list[float]:
    weights = []
    for index, scene in enumerate(scenes):
        excerpt = str(scene.get("narration_excerpt") or "")
        weights.append(max(1, len(excerpt.split())) if excerpt else max(1, len(script.split()) // len(scenes)))
    total = sum(weights)
    result = [duration * weight / total for weight in weights]
    result[-1] += duration - sum(result)
    return result

def _caption_filter(srt_path: Path, width: int) -> str:
    safe = srt_path.as_posix().replace(":", "\\:")
    font_size = 24 if width < 1500 else 32
    return f"subtitles='{safe}':force_style='FontName=DejaVu Sans,FontSize={font_size},PrimaryColour=&H00FFFFFF,OutlineColour=&H00101820,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=90'"

def render_video(render_id: str, title: str, script: str, aspect: Literal["vertical", "landscape"], scenes: list[dict] | None = None, music_filename: str | None = None, visual_mode: str = "auto") -> str:
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
        json={"text": script, "model_id": settings.elevenlabs_model_id, "voice_settings": {"stability": 0.48, "similarity_boost": 0.78}},
        timeout=settings.render_timeout_seconds,
    )
    response.raise_for_status()
    audio_path.write_bytes(response.content)
    audio_duration = _duration(audio_path)
    build_srt(script, srt_path, audio_duration)
    width, height = (1080, 1920) if aspect == "vertical" else (1920, 1080)
    scene_items = scenes or build_storyboard(script, title)
    if len(scene_items) > 8:
        raise ValueError("A maximum of 8 generated scenes is supported per render.")
    durations = _scene_durations(scene_items, script, audio_duration)
    segment_paths = []
    for index, (scene, duration) in enumerate(zip(scene_items, durations)):
        segment_path = job_dir / f"segment-{index + 1:02}.mp4"
        prompt = (
            "Create a scientifically accurate cinematic educational science video shot. "
            "No text, labels, subtitles, logos or watermark. Deep navy and electric cyan visual identity. "
            "Use coherent natural camera motion, stable geometry, physically plausible movement, "
            "clean scientific composition and no morphing of molecular structures. "
            + str(scene["prompt"])
        )
        use_motion = visual_mode == "ai" or (visual_mode == "auto" and bool(settings.replicate_api_token and settings.replicate_video_model_version))
        if use_motion:
            motion_path = job_dir / f"motion-{index + 1:02}.mp4"
            generate_motion_clip(prompt, motion_path, aspect, duration)
            _run([
                settings.ffmpeg_binary, "-y", "-i", str(motion_path), "-t", f"{duration:.3f}",
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30,format=yuv420p",
                "-an", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                "-t", f"{duration:.3f}", str(segment_path),
            ])
        else:
            image_path = job_dir / f"scene-{index + 1:02}.png"
            generate_scene_image(prompt, image_path, aspect)
            zoom = "min(zoom+0.00065,1.08)" if index % 2 == 0 else "if(lte(zoom,1.0),1.08,max(1.0,zoom-0.00065))"
            _run([
                settings.ffmpeg_binary, "-y", "-loop", "1", "-framerate", "30", "-i", str(image_path),
                "-t", f"{duration:.3f}",
                "-vf", f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,crop={width*2}:{height*2},zoompan=z='{zoom}':d=1:s={width}x{height}:fps=30,format=yuv420p,fade=t=in:st=0:d=0.35:alpha=0,fade=t=out:st={max(0,duration-0.35):.3f}:d=0.35:alpha=0",
                "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-an", "-pix_fmt", "yuv420p", str(segment_path),
            ])

    concat_file = job_dir / "scenes.txt"
    concat_file.write_text("".join(f"file '{p.name}'\n" for p in segment_paths), encoding="utf-8")
    visual_path = job_dir / "visuals.mp4"
    _run([settings.ffmpeg_binary, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(visual_path)])
    music_path = None
    if music_filename:
        if Path(music_filename).name != music_filename or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", music_filename):
            raise ValueError("Music filename must be a simple filename stored in the render job folder.")
        music_path = job_dir / music_filename
        if not music_path.is_file():
            raise ValueError("Requested music file was not found in this render's media folder.")
    caption_filter = _caption_filter(srt_path, width)
    command = [settings.ffmpeg_binary, "-y", "-i", str(visual_path), "-i", str(audio_path)]
    if music_path:
        command += ["-stream_loop", "-1", "-i", str(music_path)]
        audio_filter = "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[voice];[2:a]volume=0.12[music];[music][voice]sidechaincompress=threshold=0.025:ratio=8:attack=20:release=350[ducked];[voice][ducked]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        command += ["-vf", caption_filter, "-filter_complex", audio_filter, "-map", "0:v", "-map", "[aout]"]
    else:
        command += ["-vf", caption_filter, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-map", "0:v", "-map", "1:a"]
    command += ["-t", f"{audio_duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(video_path)]
    _run(command)
    return f"/media/{render_id}/final.mp4"
