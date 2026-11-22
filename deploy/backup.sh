#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
COMPOSE=(docker compose -f deploy/compose.production.yml --env-file .env)
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${BACKUP_DIR:-$ROOT/backups}/$STAMP"
mkdir -p "$DEST"
chmod 700 "$DEST"

"${COMPOSE[@]}" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DEST/postgres.dump"
"${COMPOSE[@]}" run --rm --no-deps --entrypoint sh api -c 'tar -czf - -C /data media private-media' > "$DEST/media.tar.gz"
(
  cd "$(dirname "$DEST")"
  sha256sum "$STAMP/postgres.dump" "$STAMP/media.tar.gz" > "$STAMP/SHA256SUMS"
)
echo "Backup written to $DEST"
echo "Copy this directory off-host and encrypt it; test restoration regularly."
