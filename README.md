# BioinfoBeats AI Studio

AI-assisted content production studio with six-agent orchestration, research, AI scene artwork, narrated FFmpeg rendering, creative assets, approval-gated Buffer publishing, YouTube analytics and account-isolated workspaces.

## Run
Copy .env.example to .env, configure credentials, then run docker compose up --build.
Dashboard: http://localhost:3000. API docs: http://localhost:8000/docs.
Set frontend NEXT_PUBLIC_API_URL to the public API URL when deploying.

## Google / YouTube owner analytics setup
1. In Google Cloud Console, create an OAuth 2.0 Web application client.
2. Enable YouTube Analytics API for the project.
3. Add the exact redirect URI from GOOGLE_OAUTH_REDIRECT_URI to the OAuth client's authorized redirect URIs.
4. Configure GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REDIRECT_URI and GOOGLE_OAUTH_FRONTEND_URL.
5. Set OAUTH_TOKEN_ENCRYPTION_KEY to a long random secret, distinct from SECRET_KEY. Refresh tokens are encrypted at rest with Fernet before database storage.
6. Sign in to the dashboard and select Connect Google account. Grant YouTube Analytics read-only permission.
7. Use the private channel report control to retrieve owner-authorized metrics.

OAuth routes:
- GET /api/v1/oauth/google/start (bearer-authenticated)
- GET /api/v1/oauth/google/callback (Google redirect)
- GET /api/v1/oauth/google/status (bearer-authenticated)
- DELETE /api/v1/oauth/google (bearer-authenticated; revokes grant)

The OAuth flow uses signed, expiring state tied to the signed-in user, server-side code exchange, encrypted refresh-token storage, automatic access-token refresh for reports and explicit disconnect/revocation. Never expose Google client secrets or refresh tokens to the browser. Configure the OAuth consent screen and publishing status in Google Cloud Console; external users may require app verification.

## Tests
cd backend && pip install -r requirements.txt && pytest
