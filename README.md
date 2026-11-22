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


## Video rendering pipeline
The production renderer now creates an AI storyboard automatically when no scene prompts are supplied, generates scene artwork, animates each scene with slow Ken Burns camera movement, aligns scene timing and sentence captions to the generated narration duration, normalizes voice audio, optionally ducks background music under narration, and exports an H.264/AAC MP4 with fast-start metadata. Select vertical 9:16 or landscape 16:9 in the dashboard. Completed MP4s can be previewed in the production desk.

This is a cinematic still-image animation workflow, not a text-to-video diffusion or live-action generative video service. Motion is created by FFmpeg camera animation; a dedicated generative video provider can be integrated as a later adapter. FFmpeg and ffprobe are installed in the backend container. Video generation requires ElevenLabs, OpenAI image generation and an LLM API key for automatic storyboards. Rendering retries transient task failures up to two times.


## Research-to-script studio
The authenticated research studio combines Tavily web search with optional YouTube Data API search, then generates a 5- or 6-minute educational narration, structured sections, worked examples, claim-to-source mappings and a separate AI fact-audit report. Retrieved source records and the generated draft are persisted per user in PostgreSQL. Source IDs are checked against the retrieved result set; unsupported source IDs are discarded and claims without valid links are marked for verification.

Configure TAVILY_API_KEY and LLM_API_KEY. YOUTUBE_API_KEY enables the additional YouTube search results. Use POST /api/v1/research/studio to generate and save a draft, GET /api/v1/research/scripts to list saved drafts, and GET /api/v1/research/scripts/{script_id} to retrieve a complete draft. Every script remains a draft for human scientific review; AI fact auditing is an assistive check, not a guarantee of correctness.


## Script editor, version history and approval handoff
Research drafts can be edited and saved through PUT /api/v1/research/scripts/{script_id}. Before each edit, the prior title, narration and section structure are captured as a numbered revision. List and inspect versions with GET /api/v1/research/scripts/{script_id}/revisions and GET /api/v1/research/scripts/{script_id}/revisions/{revision_id}; restore an earlier version with POST /api/v1/research/scripts/{script_id}/revisions/{revision_id}/restore. The script can be approved after human scientific review with POST /api/v1/research/scripts/{script_id}/approve. Approval locks further editing. Only approved scripts can be handed off to a new production workflow through POST /api/v1/research/scripts/{script_id}/workflow. The handoff includes the approved narration, research sources and fact-audit metadata; publishing remains a separate human-approved action.


## One-click approved production assembly
A workflow created through the approved Research Studio handoff can be assembled with POST /api/v1/workflows/{workflow_id}/production/assemble and body {"aspect":"vertical"} or {"aspect":"landscape"}. The authenticated, owner-scoped endpoint requires the approved research script stored on that workflow. A Celery task generates ElevenLabs narration, an AI storyboard and scene artwork, animated scene segments, timed captions and the final MP4, then generates three thumbnail concepts and platform copy. Progress is stored under workflow config.production_assembly; the MP4 is stored under config.video_render and creative assets under config.creative_package. The dashboard exposes the one-click action for eligible workflows. This is an asynchronous, provider-dependent workflow: configure ElevenLabs, OpenAI image generation, LLM and FFmpeg dependencies. Publishing is deliberately not part of assembly and still requires the separate human approval flow. Scene visuals are generated still images animated with FFmpeg, not native text-to-video clips.


## AI motion video provider (Phase 18)
The renderer supports a Replicate prediction adapter for per-scene text-to-video generation. Configure REPLICATE_API_TOKEN and REPLICATE_VIDEO_MODEL_VERSION with a model version whose input schema accepts prompt, duration (seconds) and aspect_ratio ("9:16" or "16:9"). The provider version is intentionally operator-selected because Replicate hosts multiple models with different capabilities, costs and input schemas. In the regular render endpoint, set visual_mode to "ai" to require generated motion clips, "static" to force image animation, or "auto" (default) to use motion when both credentials are configured and otherwise retain the static-image renderer. Production assembly accepts the same visual_mode option. Generated clips are normalized, muted, cropped to the requested aspect ratio and timed to each narration scene before captions and narration are mixed. AI mode fails clearly rather than silently downgrading if credentials or a compatible model version are missing. Provider generation is asynchronous and can incur per-scene charges; check model pricing and limits before enabling it. The adapter polls the Replicate prediction until completion or timeout and only downloads HTTPS output files from Replicate delivery hosts.
