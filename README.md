# BioinfoBeats AI Studio

AI-assisted content production studio with six-agent orchestration, research, video rendering, creative assets, approval-gated Buffer publishing, Google OAuth and YouTube analytics.

## Run
Copy .env.example to .env, configure credentials, then run docker compose up --build.
Dashboard: http://localhost:3000. API docs: http://localhost:8000/docs.

## Automated YouTube analytics
Celery Beat schedules a daily collection job. It retrieves a rolling seven-day YouTube Analytics report for each connected Google account and stores immutable snapshots in PostgreSQL. Configure the Google OAuth client, YouTube Analytics API and OAUTH_TOKEN_ENCRYPTION_KEY as described below. Start the beat service with Docker Compose (included). The scheduled task logs per-account failures and continues processing other connections.

Manual endpoints (bearer token required):
- POST /api/v1/analytics/youtube/collect queues a collection for the signed-in account.
- GET /api/v1/analytics/history?limit=30 returns the signed-in account's stored snapshots.
- POST /api/v1/analytics/youtube/channel fetches an ad-hoc date range.

Collection uses the previous seven complete calendar days (ending yesterday) to avoid partial current-day data. Snapshots preserve the source report and collection timestamp. This version does not yet send email/push notifications or automatically generate an LLM report after every collection.

## Google OAuth
Create a Google OAuth Web application, enable YouTube Analytics API, add GOOGLE_OAUTH_REDIRECT_URI as an authorized redirect URI, and configure GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REDIRECT_URI, GOOGLE_OAUTH_FRONTEND_URL and OAUTH_TOKEN_ENCRYPTION_KEY. Grant YouTube Analytics read-only scope. Refresh tokens are encrypted at rest.

## Provider keys
Configure LLM_API_KEY, TAVILY_API_KEY, YOUTUBE_API_KEY, Google OAuth values, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, OPENAI_API_KEY and BUFFER_ACCESS_TOKEN. Never commit real secrets.

## Tests
cd backend && pip install -r requirements.txt && pytest
