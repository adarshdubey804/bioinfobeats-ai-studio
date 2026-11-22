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
    for scene in scenes:
        requested = scene.get("duration_seconds")
        if requested is not None:
            value = float(requested)
            if not 1 <= value <= 180:
                raise ValueError("Each timeline scene duration must be between 1 and 180 seconds.")
            weights.append(value)
        else:
            excerpt = str(scene.get("narration_excerpt") or "")
            weights.append(max(1, len(excerpt.split())) if excerpt else max(1, len(script.split()) // len(scenes)))
    total = sum(weights)
    result = [duration * weight / total for weight in weights]
    result[-1] += duration - sum(result)
    return result

def _drawtext_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%").replace(",", "\\,")

def _caption_filter(srt_path: Path, width: int) -> str:
    safe = srt_path.as_posix().replace(":", "\\:")
    font_size = 24 if width < 1500 else 32
    return f"subtitles='{safe}':force_style='FontName=DejaVu Sans,FontSize={font_size},PrimaryColour=&H00FFFFFF,OutlineColour=&H00101820,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=90'"

def render_video(render_id: str, title: str, script: str, aspect: Literal["vertical", "landscape"], scenes: list[dict] | None = None, music_filename: str | None = None, visual_mode: str = "auto", music_volume: float = 0.12, scene_asset_paths: dict[int, str] | None = None, brand_logo_path: str | None = None) -> str:
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
    if not 0 <= music_volume <= 0.3:
        raise ValueError("Music volume must be between 0 and 0.3.")
    durations = _scene_durations(scene_items, script, audio_duration)
    cursor = 0.0
    timeline = []
    for index, (scene, scene_duration) in enumerate(zip(scene_items, durations)):
        timeline.append({**scene, "index": index, "start_seconds": round(cursor, 3), "end_seconds": round(cursor + scene_duration, 3), "duration_seconds": round(scene_duration, 3)})
        cursor += scene_duration
    manifest = {"title": title, "aspect": aspect, "visual_mode": visual_mode, "audio_duration_seconds": audio_duration, "music_volume": music_volume, "scenes": timeline}
    (job_dir / "storyboard.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    segment_paths = []
    for index, (scene, duration) in enumerate(zip(scene_items, durations)):
        segment_path = job_dir / f"segment-{index + 1:02}.mp4"
        transition = scene.get("transition", "fade")
        if transition not in {"fade", "cut"}:
            raise ValueError("Scene transition must be fade or cut.")
        overlay = str(scene.get("overlay_text") or "").strip()[:90]
        overlay_filter = ""
        if overlay:
            escaped = _drawtext_escape(overlay)
            overlay_filter = f",drawtext=text='{escaped}':fontcolor=white:fontsize={max(28,width//28)}:borderw=2:bordercolor=black@0.75:x=(w-text_w)/2:y=h*0.78"
        prompt = (
            "Create a scientifically accurate cinematic educational science video shot. "
            "No text, labels, subtitles, logos or watermark. Deep navy and electric cyan visual identity. "
            "Use coherent natural camera motion, stable geometry, physically plausible movement, "
            "clean scientific composition and no morphing of molecular structures. "
            + str(scene["prompt"])
        )
        selected_asset = Path(scene_asset_paths[index]).resolve() if scene_asset_paths and index in scene_asset_paths else None
        if selected_asset and not selected_asset.is_file():
            raise ValueError("A selected scene media file is missing.")
        is_video_asset = bool(selected_asset and selected_asset.suffix.lower() in {".mp4", ".webm"})
        use_motion = is_video_asset or (not selected_asset and (visual_mode == "ai" or (visual_mode == "auto" and bool(settings.replicate_api_token and settings.replicate_video_model_version))))
        if use_motion:
            motion_path = job_dir / f"motion-{index + 1:02}.mp4"
            if is_video_asset:
                motion_path = selected_asset
            else:
                generate_motion_clip(prompt, motion_path, aspect, duration)
            source_args = ["-i", str(motion_path)]
            video_filter = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30{overlay_filter},format=yuv420p"
        else:
            image_path = selected_asset or (job_dir / f"scene-{index + 1:02}.png")
            if not selected_asset:
                generate_scene_image(prompt, image_path, aspect)
            zoom = "min(zoom+0.00065,1.08)" if index % 2 == 0 else "if(lte(zoom,1.0),1.08,max(1.0,zoom-0.00065))"
            source_args = ["-loop", "1", "-framerate", "30", "-i", str(image_path)]
            video_filter = f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,crop={width*2}:{height*2},zoompan=z='{zoom}':d=1:s={width}x{height}:fps=30{overlay_filter},format=yuv420p"
        if transition == "fade":
            video_filter += f",fade=t=in:st=0:d=0.25,fade=t=out:st={max(0,duration-0.25):.3f}:d=0.25"
        command = [settings.ffmpeg_binary, "-y"] + source_args
        if brand_logo_path:
            logo = Path(brand_logo_path).resolve()
            if not logo.is_file():
                raise ValueError("Selected brand logo file is missing.")
            logo_filter = f"[1:v]scale={max(60,width//8)}:-1[brand];[0:v]{video_filter}[base];[base][brand]overlay=W-w-32:32:format=auto[vout]"
            command += ["-loop", "1", "-i", str(logo), "-filter_complex", logo_filter, "-map", "[vout]"]
        else:
            command += ["-vf", video_filter]
        command += ["-t", f"{duration:.3f}", "-an", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(segment_path)]
        _run(command)
        segment_paths.append(segment_path)

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
        audio_filter = f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[voice];[2:a]volume={music_volume}[music];[music][voice]sidechaincompress=threshold=0.025:ratio=8:attack=20:release=350[ducked];[voice][ducked]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        command += ["-vf", caption_filter, "-filter_complex", audio_filter, "-map", "0:v", "-map", "[aout]"]
    else:
        command += ["-vf", caption_filter, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-map", "0:v", "-map", "1:a"]
    command += ["-t", f"{audio_duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(video_path)]
    _run(command)
    return f"/media/{render_id}/final.mp4"
