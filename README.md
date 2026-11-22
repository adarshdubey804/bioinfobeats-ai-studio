# BioinfoBeats AI Studio

AI-assisted content production studio with six-agent orchestration, evidence collection, AI scene artwork, narrated FFmpeg video rendering and human-reviewed publishing.

## Platform
- Next.js + TypeScript dashboard
- FastAPI, PostgreSQL, SQLAlchemy, Alembic
- Redis + Celery background workers
- JWT registration/login
- Six-stage AI pipeline: topic research, fact checking, competitor research, video generation brief, editing plan, creative/publishing package
- Tavily web search and YouTube Data API research
- ElevenLabs narration, OpenAI image generation, scene assembly, sentence-level subtitles and FFmpeg MP4 export
- Publishing remains human-approved.

## Run
Copy .env.example to .env, configure credentials, then run docker compose up --build.
Dashboard: http://localhost:3000. API docs: http://localhost:8000/docs.

## Provider keys
- LLM_API_KEY: OpenAI-compatible chat completions API.
- TAVILY_API_KEY: Tavily search API.
- YOUTUBE_API_KEY: Google Cloud YouTube Data API v3.
- ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID: narration generation.
- OPENAI_API_KEY: image generation. Configure OPENAI_IMAGE_MODEL as an available image model for your account.

Never commit API keys.

## Render a scene-based video
Create a workflow, then POST /api/v1/workflows/{workflow_id}/render:
{
  "title": "BLAST explained in 5 minutes",
  "script": "Complete narration script goes here. Keep sentences concise for captions.",
  "aspect": "vertical",
  "scenes": [
    {"prompt": "A glowing DNA sequence aligning against a reference genome, cinematic macro science visualization", "duration_seconds": 8},
    {"prompt": "A clear scientific visualization of local sequence alignment with highlighted matching bases", "duration_seconds": 8}
  ]
}
Use "landscape" for standard YouTube. Up to 8 scene images are generated for each render. The worker combines them with narration and subtitles. Optional background music can be placed in that render's media directory and referenced by a safe filename in music_filename; it is mixed quietly under narration. Check music rights before use. Poll GET /api/v1/workflows/{workflow_id}; the video_render field reports status and final URL.

The current implementation creates still-image scenes with subtle motion and fades; it does not yet produce full-motion AI video, animated avatars, or auto-generated soundtracks. Image generation and narration incur provider charges.

## Research
POST /api/v1/research/web or /api/v1/research/youtube with {"query":"BLAST bioinformatics tutorial","max_results":5}.

## Workflow
POST /api/v1/workflows with topic and config, then POST /api/v1/workflows/{id}/queue. Poll GET /api/v1/workflows/{id}. Review all generated claims and media before publishing.

## Test
cd backend && pip install -r requirements.txt && pytest
