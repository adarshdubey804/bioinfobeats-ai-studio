# BioinfoBeats AI Studio

An AI-assisted social content production studio for research, competitor intelligence, video scripting, editing plans, creative briefs and human-approved publishing.

## Current implementation

- Next.js App Router + TypeScript dashboard
- FastAPI API, PostgreSQL, SQLAlchemy 2 and Alembic
- Redis + Celery background worker
- JWT registration/login and password hashing
- Six-agent sequential orchestration pipeline using an OpenAI-compatible chat-completions endpoint
- Workflow persistence with per-agent JSON output and error status
- Human approval boundary: the pipeline creates drafts and production instructions; it does not publish, schedule, render or upload media.

## Six agents

1. Topic Researcher — research brief, content angles and source queries.
2. Fact-check Researcher — claim review, caveats and verification needs.
3. Competitor Researcher — competitor research queries, hypotheses clearly labelled as such, and content gaps. No fabricated browsing.
4. AI Video Generator — script, scenes, narration and avatar-generation brief. Provider rendering is a later integration.
5. Video Editor — edit decision list, captions, transitions and export instructions. Media rendering is a later integration.
6. Creative & Publishing — poster brief, channel copy and publishing checklist. Publishing is never automatic.

## Run locally

1. Copy .env.example to .env.
2. Set a strong SECRET_KEY, database password and LLM_API_KEY.
3. Run docker compose up --build.
4. Open http://localhost:3000 and API docs at http://localhost:8000/docs.

API example: POST /api/v1/workflows with JSON containing topic and config fields such as brand, audience, platforms, format, target_duration_seconds and competitors.

Then call POST /api/v1/workflows/{id}/queue. Poll GET /api/v1/workflows/{id}. When complete, status is ready_for_review and agent_outputs contains each agent's structured result. If the provider key is missing or a call fails, status becomes failed and pipeline_error explains why.

## Authentication

- POST /api/v1/auth/register
- POST /api/v1/auth/login
- GET /api/v1/auth/me with Authorization: Bearer <token>

## Tests

From backend: pip install -r requirements.txt, then pytest.

## Next integrations

External web search for verified research and competitor evidence; AI avatar/video provider; FFmpeg rendering; poster image generation; Buffer account authorization and publishing; analytics and approval UI.

Never commit credentials. Configure production CORS, TLS, secret management, rate limiting, backups and access controls before deployment.
