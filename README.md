# BioinfoBeats AI Studio

A modular AI-assisted social content production studio coordinating research, competitor intelligence, scripting, avatar/video generation, editing, creative assets and social publishing through a human-reviewed workflow.

> Status: foundation scaffold. External AI/video/avatar and social publishing integrations require provider credentials and implementation/testing. Nothing is published without explicit approval.

## Architecture
- Web: Next.js App Router + TypeScript
- API: FastAPI + Pydantic settings
- Persistence: PostgreSQL + SQLAlchemy 2 + Alembic
- Jobs: Redis + Celery
- Agents: six modular agent specs behind a shared interface; provider adapters remain separate from orchestration

## Six agents
1. Topic Researcher — discover topics and source material.
2. Fact-check Researcher — verify claims and attach references.
3. Competitor Researcher — review public competitor content and identify gaps.
4. AI Video Generator — prepare narration/avatar generation requests through a configured provider.
5. Video Editor — build edit plans and hand off media operations to FFmpeg/provider adapters.
6. Creative & Publishing — create poster briefs/assets and prepare channel-specific publishing jobs via Buffer/provider adapters.

## Quick start
1. Copy `.env.example` to `.env` and change local secrets.
2. Run `docker compose up --build`.
3. Web app: http://localhost:3000; API docs: http://localhost:8000/docs; health: http://localhost:8000/api/v1/health.

The API container runs Alembic migrations before startup. For local development without Docker, install `backend/requirements.txt`, set `DATABASE_URL` and `REDIS_URL`, run `alembic upgrade head`, then `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` from `backend`.

## API foundation
- `GET /api/v1/health` — liveness check.
- `GET /api/v1/agents` — registered agent descriptions.
- `POST /api/v1/workflows` — create workflow in `draft` state.
- `GET /api/v1/workflows/{id}` — inspect state.
- `POST /api/v1/workflows/{id}/queue` — queue for worker execution.

Queueing is not publication. The initial worker creates a deterministic demo execution record; real providers and agent execution are Phase 2+.

## Checks
Backend: `cd backend && pytest`. Frontend: `cd frontend && npm install && npm run lint && npm run build`.

## Security
- Never commit `.env` or provider credentials.
- Use strong unique secrets outside local development.
- Configure exact CORS origins in production; terminate TLS at ingress.
- Add OAuth/provider account authorization and token encryption before real publishing.
- Keep human approval enabled before external publishing/scheduling.

## Planned phases
1. Platform foundation (this scaffold).
2. Agent prompts, tools, LangGraph orchestration, durable run state and provenance.
3. Research and competitor provider integrations.
4. AI avatar/video generation adapters and FFmpeg editing pipeline.
5. Poster/thumbnail generation, Buffer integration and approval UI.
6. Analytics, retries, observability, permissions and production hardening.
