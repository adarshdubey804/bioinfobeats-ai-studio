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


## Scene storyboard editor (Phase 19)
Every completed render stores its storyboard manifest alongside media files. Authenticated workflow owners can load it with GET /api/v1/workflows/{workflow_id}/editor/storyboard and update scene prompts, narration excerpts and transition metadata with PUT /api/v1/workflows/{workflow_id}/editor/storyboard. The dashboard provides a scene-by-scene prompt editor and displays available generated still-image previews. Save the storyboard, then queue a new render to apply the revised scene list; the prior MP4 remains available until the new render completes. Scene editing is prompt/manifest editing rather than a frame-accurate nonlinear timeline. The transition value is retained in the manifest for future transition rendering support.


## Scientific Visual Intelligence (Phase 20)
Authenticated users can generate reusable SVG assets through POST /api/v1/visuals/{kind}, where kind is dna, pathway, alignment or phylogeny. The DNA output is a stylized schematic. Pathway diagrams accept 2–16 labeled nodes and up to 32 directed edges. Sequence alignments accept 2–8 equal-length strings (up to 100 columns) using supported nucleotide/IUPAC symbols. Phylogeny output is an illustrative topology from 2–12 labels, not an inferred evolutionary tree. Assets are saved under media/scientific-assets and returned as SVG URLs. These are schematic educational graphics, not validated biological analyses; verify every scientific claim and reference before publication. 


## Scientific Animation Studio (Phase 21)
Authenticated POST /api/v1/visuals/animate/{kind} generates five-second 960×540, 24 FPS MP4 motion graphics. Supported kinds: dna, central_dogma, pathway, alignment and phylogeny. Pathway animations accept 2–10 nodes and up to 20 edges; alignment accepts 2–6 equal-length nucleotide/IUPAC sequences up to 50 columns; phylogeny accepts 2–8 labels. The backend uses Pillow to draw frames and FFmpeg to encode MP4. Install the updated backend requirements and ensure FFmpeg is installed in the runtime image. Generation is synchronous and may take several seconds; large concurrent render volumes should be moved to Celery. These clips are schematic educational animations, not molecular simulations or computationally inferred results. 


## Professional timeline controls (Phase 22)
The storyboard editor now includes a proportional scene timeline, narration/music track indicators, per-scene duration weights and background music gain. Scene duration values are relative weights that are normalized to the actual generated narration duration, so the final video remains synchronized to the voice track. Set music_volume between 0 and 0.3 in POST /api/v1/workflows/{workflow_id}/render; the dashboard exposes this control. Scene timing and gain are saved with the storyboard and passed into a new render. Transition choices remain metadata only in this phase; crossfades, drag-and-drop reordering, waveform editing, and independent audio tracks are not yet implemented. 


## Advanced editing and export controls (Phase 23)
The storyboard editor supports moving scenes earlier/later, per-scene text overlays/lower-thirds, duration weights, and cut/fade transition choices. During rendering, overlay text is burned into each scene and fade transitions fade that scene at its boundaries; cut leaves boundaries hard. Select vertical (9:16) for Shorts/Reels or landscape (16:9) for YouTube long-form. Save the storyboard before queueing a render. This remains a lightweight scene editor rather than a full nonlinear editing suite: there is no waveform display, independent clip trimming, multitrack timeline, or true overlapping crossfade. The renderer outputs H.264/AAC MP4. 


## Media Library (Phase 24)
The authenticated media library stores reusable user-owned assets in the shared media volume and records metadata in PostgreSQL. Upload with POST /api/v1/media/library?media_type=image|audio|video using multipart field "file"; list with GET /api/v1/media/library?q=&media_type=all|image|audio|video; delete with DELETE /api/v1/media/library/{asset_id}. Uploads are limited to 50 MB and allowlisted JPEG, PNG, WebP, MP3, WAV, OGG, MP4 and WebM. Each account sees and manages only its own records. Media files are served by the existing /media static mount, so possession of a media URL grants access to that file; do not upload confidential assets. Files persist in the Docker media_data volume. The editor and render pipeline can select library images/videos for individual scenes, background music, and a brand logo. Media URLs are served by the shared static mount and are therefore shareable by anyone who obtains the URL; do not upload confidential material.


## Media-to-video scene integration (Phase 25)
Render requests may attach a user-owned image/video asset to each scene using scenes[].asset_id, select background music with music_asset_id, and add an image watermark with brand_logo_asset_id. The API verifies ownership and media category before queueing. The worker rechecks ownership, copies selected assets into the render job directory, and the renderer uses uploaded stills or video clips instead of generating those scene visuals. Uploaded music is copied into the render directory and mixed beneath narration; the selected image logo is composited in the upper-right of each scene. Existing generated visuals remain the default when no scene asset is selected. Save the storyboard to preserve scene asset selections; logo selection is saved in the storyboard manifest when supported by the editor endpoint. Direct asset file URLs are served by the existing public static media mount, so treat them as shareable URLs.


## AI voice and pronunciation controls (Phase 29)
Video render requests accept optional `voice_id`, `voice_stability` (0–1), `voice_similarity` (0–1), `voice_speed` (0.7–1.2), and `pronunciation_dictionary` (up to 3000 characters). Leave voice_id blank to use ELEVENLABS_VOICE_ID. Pronunciation entries use one `term=spoken form` per line and are applied to narration text before synthesis; the original script remains the editorial source for captions and storyboard. The dashboard exposes voice ID, stability, similarity, speed, pronunciation mapping, and existing music gain. Voice IDs must belong to the configured ElevenLabs account. The dashboard also supports voice catalog selection, short authenticated audio previews, and browser-local voice presets. Presets are not synced across devices.


## Voice library, previews and presets (Phase 30)
The authenticated `GET /api/v1/audio/voices` endpoint lists voices available to the configured ElevenLabs account. `POST /api/v1/audio/voice-preview` accepts `text` (10–800 chars), `voice_id`, `stability` (0–1), `similarity` (0–1), and `speed` (0.7–1.2), then returns a private preview ID. Fetch the MP3 through authenticated `GET /api/v1/audio/voice-preview/{preview_id}`; the server verifies ownership and marks the response private/no-store. Preview files are stored beneath the user's `voice_previews` directory on the media volume. The dashboard can load the catalog, audition a short sample, and save/apply voice presets in browser local storage. Presets are browser-local and are not synced across devices. ElevenLabs credentials remain server-side.


## Rendering scale update
The render API and storyboard editor support up to 20 scenes per video. This is a practical throughput limit rather than an absolute architectural ceiling; very large scene counts increase image/video provider cost and FFmpeg render time. Provider quotas, file sizes, hardware and platform upload rules remain external constraints.


## One-click production settings and retry behavior
The approved-production assembly request accepts the same scene, media, music, and voice settings as an individual render. It validates selected media ownership before queueing, copies selected assets into the render job folder, and records voice settings in the storyboard manifest. Production assembly resumes at the creative-package stage if the video render has already completed, avoiding an unnecessary second render on a thumbnail-generation retry. Worker tasks retry transient failures with bounded exponential backoff. Publishing is never triggered by assembly.

## Continuous integration and deployment smoke test
GitHub Actions runs the backend pytest suite, the Next.js production build, and a Docker Compose smoke test. The smoke test starts PostgreSQL, Redis, API, Celery worker/beat and frontend; waits for database/Redis readiness; registers and authenticates a test account; and checks the authenticated workflow endpoint. A passing CI run validates the containerized application foundation, not external provider credentials or paid provider availability.

## Operational boundaries
External providers impose their own quotas, costs, account permissions, rate limits, and model availability. Configure valid credentials before enabling provider-backed features. The renderer currently limits a request to 20 scenes; media uploads are limited to 50 MB; voice previews accept at most 800 characters. Public static media URLs are shareable and are not suitable for private or regulated content. A real production deployment should add private object storage/CDN access controls, backups, HTTPS, secret rotation, monitoring, and a managed queue/database. No codebase can remove third-party quotas or platform publishing rules.


## Media privacy and storage layout
The public static mount now serves only files under `MEDIA_STORAGE_DIR/public`: rendered videos, creative thumbnails, and generated educational visuals/animations. Uploaded media-library originals remain under `MEDIA_STORAGE_DIR/library` and are delivered through the authenticated owner-scoped `GET /api/v1/media/library/{asset_id}/file` endpoint with private/no-store caching. Voice previews are stored separately under `PRIVATE_MEDIA_STORAGE_DIR` and are retrieved only through the authenticated preview endpoint. Set `PRIVATE_MEDIA_STORAGE_DIR` to a persistent private volume in deployment. Existing deployments should retain their media volume and back it up before upgrading; previously exposed media URLs should be considered shareable until old links are retired. This change protects new library and preview requests, but public final video/thumbnail URLs are intentionally still shareable.


## Persistent background job history
Agent pipeline queueing and one-click production assembly each create a durable `job_runs` record (migration `0010_job_runs`). Records retain task type, Celery task ID, status, progress payload, retry attempt count, error details, and lifecycle timestamps. Authenticated owners can inspect the latest 50 runs for a workflow with `GET /api/v1/workflows/{workflow_id}/jobs`. Production render-stage progress updates the corresponding run; completion and bounded retry/failure outcomes are recorded. This is application-level execution history, not a guarantee that a task survives loss of the Redis broker; deploy Redis with persistence and backups, and monitor stale running jobs.


### Background job cancellation
Authenticated users can request cancellation with `POST /api/v1/workflows/{workflow_id}/jobs/{job_id}/cancel`. Queued tasks are revoked without worker termination. Running tasks receive a cooperative cancellation request and stop at their next supported safe checkpoint; a video render already executing FFmpeg/provider work is not force-killed, so it may finish that stage before cancellation is acknowledged. Cancelled workflows can be queued again. The API returns `cancelling` while a running worker is reaching its checkpoint.


### Safe stale-job recovery
Queue endpoints reject a workflow that already has an active background job. A stale job can be closed through `POST /api/v1/workflows/{workflow_id}/jobs/{job_id}/recover` with `{"worker_stopped":true}` only after an operator has verified that the old worker process is stopped. The API checks the stale threshold, requests Celery revocation, closes the old run and permits a new queue. This is deliberately a manual safety gate: revocation alone does not terminate an already-running task, and blindly replaying a task could duplicate provider charges or production assets.


### API protection and media quotas
Authentication registration is limited to 5 requests per IP per minute; login to 10 per minute; media uploads to 20 per IP per minute. Limits use Redis shared across API instances and return HTTP 503 if Redis is unavailable (fail-closed). Each account has a 1 GiB media-library quota, reserved atomically when an upload is accepted and released when an asset is deleted. Individual uploads remain capped at 50 MiB. These are baseline controls; production deployments should add edge/WAF limits and monitor Redis availability.


### Provider readiness and live validation
Authenticated operators can inspect `GET /api/v1/health/providers` for a secret-free inventory of configured provider credentials. The endpoint checks configuration presence only; it does not validate keys, make paid requests, prove quota availability, or guarantee model access. The core pipeline expects an LLM key, Tavily, ElevenLabs API key plus voice ID, and an OpenAI image key. Replicate, Buffer and Google OAuth are optional capabilities. Run a small controlled end-to-end test with real credentials before enabling production workloads.


## Production deployment
A single-host production Compose topology with Caddy TLS termination, internal-only application/database/cache services, persistent volumes, health checks and bounded container logs is provided in `deploy/`. Follow [deploy/PRODUCTION.md](deploy/PRODUCTION.md). Backups: `bash deploy/backup.sh`; destructive restore instructions: [deploy/RESTORE.md](deploy/RESTORE.md). This is a single-host baseline, not a high-availability deployment. Test restores on staging and maintain encrypted off-host backups.
