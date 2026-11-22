# Production restore runbook

This procedure is destructive. Restore into a maintenance window after stopping API and workers, and verify the backup checksums first.

1. Copy the backup directory to the production host and run `sha256sum -c SHA256SUMS` from inside it.
2. Stop application writers: `docker compose -f deploy/compose.production.yml --env-file .env stop api worker beat`.
3. Restore PostgreSQL (this replaces the target database):
   ```sh
   docker compose -f deploy/compose.production.yml --env-file .env exec -T db sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < postgres.dump
   ```
4. Restore media files into the shared media volume:
   ```sh
   docker compose -f deploy/compose.production.yml --env-file .env run --rm --no-deps --entrypoint sh api -c 'tar -xzf - -C /data' < media.tar.gz
   ```
5. Start services and verify `/api/v1/health/ready`, login, media previews and a small test render.

The archive contains user media and database records. Restrict access, encrypt off-host copies, define retention, and test recovery at a cadence appropriate to your recovery-point objective. This runbook is a starting point; validate it on a staging copy before relying on it.
