# BioinfoBeats AI Studio

AI-assisted content production studio with six-agent orchestration, evidence collection and human-reviewed publishing.

## Platform
- Next.js + TypeScript dashboard
- FastAPI, PostgreSQL, SQLAlchemy, Alembic
- Redis + Celery
- JWT registration/login
- Six-stage AI pipeline: topic research, fact checking, competitor research, video generation brief, editing plan, creative/publishing package
- Research provider adapters: Tavily web search and YouTube Data API
- Publishing is not automatic; human approval remains mandatory.

## Run
Copy .env.example to .env, configure credentials, then run docker compose up --build.
Dashboard: http://localhost:3000. API docs: http://localhost:8000/docs.

## Provider keys
- LLM_API_KEY: OpenAI-compatible chat completions API.
- TAVILY_API_KEY: Tavily search API for web evidence retrieval.
- YOUTUBE_API_KEY: Google Cloud YouTube Data API v3 key.

Never commit API keys. Set production secrets in your deployment environment.

## Research endpoints
POST /api/v1/research/web
POST /api/v1/research/youtube

Body: {"query":"BLAST bioinformatics tutorial","max_results":5}
Responses preserve source titles, URLs, snippets and metadata from providers. Search results are evidence candidates, not endorsements or verified facts; the fact-check stage must inspect source material.

## Workflow
POST /api/v1/workflows with topic and config, then POST /api/v1/workflows/{id}/queue. Poll GET /api/v1/workflows/{id}. Completed agent output is marked ready_for_review. Failed provider calls set failed status with a diagnostic.

## Test
cd backend && pip install -r requirements.txt && pytest

## Roadmap
Next: enrich competitor research with channel/video statistics, connect video/avatar provider adapters, FFmpeg rendering, image creative generation and approved publishing integration.
