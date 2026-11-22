# BioinfoBeats AI Studio

AI-assisted content production studio with six-agent orchestration, research, AI scene artwork, narrated FFmpeg rendering, creative assets, approval-gated Buffer publishing, YouTube analytics and a production dashboard.

## Platform
- Next.js + TypeScript interactive dashboard
- FastAPI, PostgreSQL, SQLAlchemy, Alembic
- Redis + Celery background workers
- JWT registration/login API foundation
- Six-stage AI pipeline, Tavily web research and YouTube Data API search
- ElevenLabs narration, OpenAI scene and thumbnail generation, subtitles and FFmpeg MP4 export
- Buffer GraphQL channel lookup and explicit approval-gated scheduling
- YouTube public video statistics, owner-authorized channel analytics and AI performance insights

## Run
Copy .env.example to .env, configure server-side credentials, then run docker compose up --build.
Dashboard: http://localhost:3000. API docs: http://localhost:8000/docs.

The frontend reads NEXT_PUBLIC_API_BASE_URL (default http://localhost:8000/api/v1). For a deployed frontend set it to the public API base URL and rebuild the frontend image.

## Dashboard
Create a workflow, queue the six-agent pipeline, enter reviewed narration, queue creative assets or an MP4 render, load Buffer channels and explicitly approve a post, and fetch public YouTube statistics by video ID. The selected workflow refreshes periodically while open.

## Provider keys
Configure LLM_API_KEY, TAVILY_API_KEY, YOUTUBE_API_KEY, YOUTUBE_OAUTH_ACCESS_TOKEN, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, OPENAI_API_KEY and BUFFER_ACCESS_TOKEN as needed. Never commit real secrets.

## YouTube analytics
- POST /api/v1/analytics/youtube/videos with {"video_ids":["VIDEO_ID"]} retrieves public views, likes, comments, title, publish date and duration.
- POST /api/v1/analytics/youtube/channel with start_date and end_date retrieves owner-only watch-time and retention metrics using an OAuth access token with YouTube Analytics read-only scope.
- POST /api/v1/analytics/insights analyzes supplied metrics.

Public statistics do not expose private watch-time or retention data. OAuth consent and refresh-token management are not yet built into this version.

## Tests
cd backend && pip install -r requirements.txt && pytest
