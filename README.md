# BioinfoBeats AI Studio

AI-assisted content production studio with six-agent orchestration, evidence collection, AI scene artwork, narrated FFmpeg rendering and a creative asset pipeline.

## Platform
- Next.js + TypeScript dashboard
- FastAPI, PostgreSQL, SQLAlchemy, Alembic
- Redis + Celery background workers
- JWT registration/login
- Six-stage AI pipeline: topic research, fact checking, competitor research, video generation brief, editing plan, creative/publishing package
- Tavily web search and YouTube Data API research
- ElevenLabs narration, OpenAI scene and thumbnail generation, subtitles and FFmpeg MP4 export
- Human approval remains required before publishing.

## Run
Copy .env.example to .env, configure credentials, then run docker compose up --build.
Dashboard: http://localhost:3000. API docs: http://localhost:8000/docs.

## Provider keys
- LLM_API_KEY: OpenAI-compatible chat completions API.
- TAVILY_API_KEY: Tavily search API.
- YOUTUBE_API_KEY: Google Cloud YouTube Data API v3.
- ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID: narration generation.
- OPENAI_API_KEY: image generation. Configure OPENAI_IMAGE_MODEL to a supported image model.

Never commit API keys.

## Generate a video
POST /api/v1/workflows/{workflow_id}/render with title, script, aspect, and optional scenes (up to 8). Poll GET /api/v1/workflows/{workflow_id} for video_render status and MP4 URL.

## Generate thumbnails and platform copy
POST /api/v1/workflows/{workflow_id}/creative:
{
  "title": "BLAST explained in 5 minutes",
  "script": "The approved narration script...",
  "platforms": ["YouTube", "Instagram", "LinkedIn"]
}
The background worker creates three thumbnail concepts/images, a YouTube title and description, hashtags, and platform captions. Results are saved in workflow.creative_package and image URLs are served from /media. Review all claims, copy and images before publishing.

## Research
POST /api/v1/research/web or /api/v1/research/youtube with {"query":"BLAST bioinformatics tutorial","max_results":5}.

## Tests
cd backend && pip install -r requirements.txt && pytest
