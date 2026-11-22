"""Replicate video-generation adapter. Model/version and input schema are configured by the operator."""
from pathlib import Path
from urllib.parse import urlparse
import time
import httpx
from app.core.config import settings

class MotionProviderError(RuntimeError):
    pass

def generate_motion_clip(prompt: str, output: Path, aspect: str, duration_seconds: float) -> None:
    token=settings.replicate_api_token
    version=settings.replicate_video_model_version
    if not token or not version:
        raise MotionProviderError("AI motion mode requires REPLICATE_API_TOKEN and REPLICATE_VIDEO_MODEL_VERSION.")
    seconds=max(2,min(10,int(round(duration_seconds))))
    ratio="9:16" if aspect=="vertical" else "16:9"
    headers={"Authorization":f"Bearer {token}","Content-Type":"application/json","Prefer":"wait"}
    payload={"version":version,"input":{"prompt":prompt,"duration":seconds,"aspect_ratio":ratio}}
    with httpx.Client(timeout=settings.render_timeout_seconds) as client:
        response=client.post("https://api.replicate.com/v1/predictions",headers=headers,json=payload)
        response.raise_for_status()
        job=response.json()
        deadline=time.monotonic()+settings.motion_generation_timeout_seconds
        while job.get("status") not in {"succeeded","failed","canceled"}:
            if time.monotonic()>=deadline:
                raise MotionProviderError("Replicate video generation timed out; inspect the provider dashboard for the job.")
            poll_url=(job.get("urls") or {}).get("get")
            if not poll_url or urlparse(poll_url).hostname not in {"api.replicate.com"}:
                raise MotionProviderError("Video provider returned an invalid prediction polling URL.")
            time.sleep(settings.motion_poll_interval_seconds)
            poll=client.get(poll_url,headers={"Authorization":f"Bearer {token}"})
            poll.raise_for_status()
            job=poll.json()
        if job.get("status")!="succeeded":
            raise MotionProviderError("Replicate video generation did not succeed: "+str(job.get("error") or job.get("status")))
        result=job.get("output")
        video_url=result[0] if isinstance(result,list) and result else result
        parsed=urlparse(video_url or "")
        host=parsed.hostname or ""
        if parsed.scheme!="https" or not (host=="replicate.delivery" or host.endswith(".replicate.delivery")):
            raise MotionProviderError("Video provider returned an unsupported output URL.")
        download=client.get(video_url,timeout=settings.render_timeout_seconds)
        download.raise_for_status()
        if not download.content:
            raise MotionProviderError("Video provider returned an empty video file.")
        output.write_bytes(download.content)
