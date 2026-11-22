# BioinfoBeats AI Studio

AI-assisted content production studio with six-agent orchestration, evidence collection, AI scene artwork, narrated FFmpeg rendering, creative assets, approval-gated Buffer publishing and YouTube analytics.

## Platform
- Next.js + TypeScript dashboard
- FastAPI, PostgreSQL, SQLAlchemy, Alembic
- Redis + Celery background workers
- JWT registration/login
- Six-stage AI pipeline, Tavily web research and YouTube Data API search
- ElevenLabs narration, OpenAI scene and thumbnail generation, subtitles and FFmpeg MP4 export
- Buffer GraphQL channel lookup and explicit approval-gated scheduling
- YouTube public video statistics and owner-authorized channel analytics
- AI performance summaries grounded in submitted metrics

## Run
Copy .env.example to .env, configure credentials, then run docker compose up --build.
Dashboard: http://localhost:3000. API docs: http://localhost:8000/docs.

## Provider keys
Configure LLM_API_KEY, TAVILY_API_KEY, YOUTUBE_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, OPENAI_API_KEY and BUFFER_ACCESS_TOKEN as needed. Never commit real secrets.

## Video and creative assets
POST /api/v1/workflows/{workflow_id}/render with title, script, aspect and optional scenes. POST /api/v1/workflows/{workflow_id}/creative with title, script and platforms.

## Buffer publishing
GET /api/v1/publishing/channels for connected channels. POST /api/v1/workflows/{workflow_id}/publishing/approve with approved=true and a future timezone-aware scheduled_at, or publish_now=true. Publishing remains an explicit user-approved action.

## YouTube analytics
- POST /api/v1/analytics/youtube/videos with {"video_ids":["VIDEO_ID"]} retrieves public views, likes, comments, title, publish date and duration. Engagement rate is calculated as (likes + comments) / views × 100.
- POST /api/v1/analytics/youtube/channel with {"start_date":"2026-11-01","end_date":"2026-11-22"} retrieves owner-only channel views, likes, comments, watch time, average view duration, average view percentage and subscribers gained.
- POST /api/v1/analytics/insights with {"topic":"Bioinformatics education","videos":[...]} generates cautious recommendations based only on supplied metrics.

Public video statistics use the YouTube Data API key. Owner analytics requires an OAuth access token with the Google YouTube Analytics read-only scope. The current version accepts a configured access token; it does not yet implement OAuth consent, refresh-token storage, automatic scheduled sync, or Instagram/LinkedIn analytics. Public statistics do not expose private watch-time or retention data.

## Research
POST /api/v1/research/web or /api/v1/research/youtube with {"query":"BLAST bioinformatics tutorial","max_results":5}.

## Tests
cd backend && pip install -r requirements.txt && pytest
