# BioinfoBeats AI Studio

AI-assisted content production studio with six-agent orchestration, evidence collection, AI scene artwork, narrated FFmpeg rendering, creative assets and approval-gated Buffer publishing.

## Platform
- Next.js + TypeScript dashboard
- FastAPI, PostgreSQL, SQLAlchemy, Alembic
- Redis + Celery background workers
- JWT registration/login
- Six-stage AI pipeline, Tavily web research and YouTube Data API search
- ElevenLabs narration, OpenAI scene and thumbnail generation, subtitles and FFmpeg MP4 export
- Buffer GraphQL channel lookup and explicit approval-gated scheduling

## Run
Copy .env.example to .env, configure credentials, then run docker compose up --build.
Dashboard: http://localhost:3000. API docs: http://localhost:8000/docs.

## Provider keys
Configure LLM_API_KEY, TAVILY_API_KEY, YOUTUBE_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, OPENAI_API_KEY and BUFFER_ACCESS_TOKEN as needed. Never commit real secrets.

## Video and creative assets
POST /api/v1/workflows/{workflow_id}/render with title, script, aspect and optional scenes. POST /api/v1/workflows/{workflow_id}/creative with title, script and platforms to generate three thumbnail concepts and social copy.

## Buffer publishing
1. Create a Buffer API key in Buffer Settings → API and set BUFFER_ACCESS_TOKEN.
2. GET /api/v1/publishing/channels to retrieve your connected channel IDs.
3. Review the final content and then call POST /api/v1/workflows/{workflow_id}/publishing/approve:
{
  "channel_id": "your-buffer-channel-id",
  "text": "Your reviewed post copy",
  "approved": true,
  "scheduled_at": "2026-12-01T10:30:00+05:30",
  "publish_now": false
}
For immediate publishing, set publish_now true and omit scheduled_at. The approval endpoint is the only path that submits a post to Buffer. The API records the returned post ID, status, due time and external link. A workflow may be submitted once to avoid accidental duplicates.

Buffer uses GraphQL at https://api.buffer.com and Bearer-token authentication. Confirm channel-specific requirements and media support in Buffer's docs before using media posts. This initial integration schedules text posts only.

## Research
POST /api/v1/research/web or /api/v1/research/youtube with {"query":"BLAST bioinformatics tutorial","max_results":5}.

## Tests
cd backend && pip install -r requirements.txt && pytest
