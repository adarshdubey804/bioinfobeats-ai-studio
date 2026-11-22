# BioinfoBeats AI Studio

AI-assisted content production studio with six-agent orchestration, evidence collection, first-cut video rendering and human-reviewed publishing.

## Platform
- Next.js + TypeScript dashboard
- FastAPI, PostgreSQL, SQLAlchemy, Alembic
- Redis + Celery background workers
- JWT registration/login
- Six-stage AI pipeline: topic research, fact checking, competitor research, video generation brief, editing plan, creative/publishing package
- Tavily web search and YouTube Data API research endpoints
- First-cut video renderer: ElevenLabs narration, sentence-level SRT captions, FFmpeg MP4 export
- Publishing remains human-approved; rendering never publishes content.

## Run
Copy .env.example to .env, configure credentials, then run docker compose up --build.
Dashboard: http://localhost:3000. API docs: http://localhost:8000/docs.

## Provider keys
- LLM_API_KEY: OpenAI-compatible chat completions API.
- TAVILY_API_KEY: Tavily search API.
- YOUTUBE_API_KEY: Google Cloud YouTube Data API v3.
- ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID: narration generation.

Never commit API keys. Set production secrets in your deployment environment.

## Research
POST /api/v1/research/web or /api/v1/research/youtube
Body: {"query":"BLAST bioinformatics tutorial","max_results":5}

## Video rendering
Create a workflow, then POST /api/v1/workflows/{workflow_id}/render:
{"title":"BLAST explained in 5 minutes","script":"Your complete narration script goes here. Use short, clear sentences for captions.","aspect":"vertical"}
Use aspect "vertical" for 1080x1920 Shorts/Reels or "landscape" for 1920x1080 YouTube. Poll GET /api/v1/workflows/{workflow_id}; video_render.status progresses through queued, rendering, ready_for_review or failed. When ready, video_render.url points to the MP4 under /media. The renderer currently creates a branded static-background first cut with narration and captions; it does not yet create AI avatars, scene footage, music or transitions.

## Workflow
POST /api/v1/workflows with topic and config, then POST /api/v1/workflows/{id}/queue. Poll GET /api/v1/workflows/{id}. Agent output is marked ready_for_review.

## Test
cd backend && pip install -r requirements.txt && pytest
