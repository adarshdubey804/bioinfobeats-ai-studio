# Production deployment

## Prerequisites
- A Linux host with Docker Engine and the Compose plugin.
- A DNS A/AAAA record for the host and inbound TCP 80/443 (UDP 443 optional for HTTP/3).
- A domain name in `APP_DOMAIN`; Caddy obtains and renews TLS certificates automatically.
- Provider credentials configured in the root `.env`.

## Configure
1. Copy `.env.example` to `.env`; never commit it.
2. Set strong unique values for `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `SECRET_KEY`, and `OAUTH_TOKEN_ENCRYPTION_KEY`.
3. Set `APP_DOMAIN` to the public DNS name.
4. Set `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@db:5432/DBNAME`.
5. Set `REDIS_URL=redis://:REDIS_PASSWORD@redis:6379/0`.
6. Set `CORS_ORIGINS=https://APP_DOMAIN`.
7. Set `GOOGLE_OAUTH_REDIRECT_URI=https://APP_DOMAIN/api/v1/oauth/google/callback` and `GOOGLE_OAUTH_FRONTEND_URL=https://APP_DOMAIN`.
8. Review all provider keys and OAuth callback URLs before accepting users.

## Start and verify
```sh
docker compose -f deploy/compose.production.yml --env-file .env config
docker compose -f deploy/compose.production.yml --env-file .env up -d --build
docker compose -f deploy/compose.production.yml --env-file .env ps
curl -fsS https://$APP_DOMAIN/api/v1/health/ready
```

The production topology exposes only Caddy on public ports 80/443. PostgreSQL, Redis, API, worker and frontend have no host-published ports. Caddy routes `/api/*` and `/media/*` to the API and all other paths to Next.js. Database, Redis, media and Caddy state use named volumes. API/worker/beat use restart policies and bounded JSON-file logs.

## Backups and operations
Run `bash deploy/backup.sh` on a schedule, copy backups off-host, encrypt them, and configure retention. See [RESTORE.md](RESTORE.md). Monitor disk capacity, container restarts, provider spend, queue age, stale jobs and health readiness. Use an external uptime monitor for the HTTPS endpoint. Do not treat a successful container start as proof that paid providers work.

## Important limits
This Compose deployment is a single-host baseline, not a highly available architecture. It does not configure managed secrets, automated backup scheduling, off-site replication, alert delivery, object storage, horizontal scaling, or disaster-recovery guarantees. Configure these according to the service's expected traffic and recovery objectives. Perform a staging restore test before production launch.
