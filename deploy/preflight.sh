#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ENV_FILE="${1:-.env}"
if [[ "$ENV_FILE" != /* ]]; then ENV_FILE="$ROOT/$ENV_FILE"; fi

fail() { echo "PRE-FLIGHT FAILED: $1" >&2; exit 1; }
[[ -f "$ENV_FILE" ]] || fail "Environment file not found: $ENV_FILE"

value() {
  local key="$1"
  local line
  line="$(grep -m1 -E "^[[:space:]]*${key}=" "$ENV_FILE" || true)"
  line="${line#*=}"
  line="${line%$'\r'}"
  line="${line%\"}"; line="${line#\"}"
  line="${line%\'}"; line="${line#\'}"
  printf '%s' "$line"
}
required() {
  local key="$1" val
  val="$(value "$key")"
  [[ -n "$val" ]] || fail "$key is missing or empty"
  printf '%s' "$val"
}

domain="$(required APP_DOMAIN)"
[[ "$domain" != *example.com* && "$domain" != localhost && "$domain" != *" "* ]] || fail "APP_DOMAIN must be your real public DNS name"
[[ "$domain" == *.* ]] || fail "APP_DOMAIN must be a fully qualified domain name"

for key in POSTGRES_PASSWORD REDIS_PASSWORD SECRET_KEY OAUTH_TOKEN_ENCRYPTION_KEY; do
  secret="$(required "$key")"
  [[ "$secret" != *change-this* && "$secret" != *replace-with* && "$secret" != *use-a-long-random-secret* ]] || fail "$key still contains a sample placeholder"
  if [[ "$key" == "SECRET_KEY" || "$key" == "OAUTH_TOKEN_ENCRYPTION_KEY" ]]; then
    (( ${#secret} >= 32 )) || fail "$key must contain at least 32 characters"
  else
    (( ${#secret} >= 20 )) || fail "$key must contain at least 20 characters"
  fi
done

db_url="$(required DATABASE_URL)"
[[ "$db_url" == postgresql+psycopg://*@db:5432/* ]] || fail "DATABASE_URL must use the production db service hostname and psycopg driver"
redis_url="$(required REDIS_URL)"
[[ "$redis_url" == redis://:*@redis:6379/* ]] || fail "REDIS_URL must authenticate to the production redis service"

cors="$(required CORS_ORIGINS)"
[[ "$cors" == "https://$domain" ]] || fail "CORS_ORIGINS must be exactly https://$domain"
redirect="$(required GOOGLE_OAUTH_REDIRECT_URI)"
[[ "$redirect" == "https://$domain/api/v1/oauth/google/callback" ]] || fail "Google OAuth redirect URI must use the production HTTPS callback"
frontend="$(required GOOGLE_OAUTH_FRONTEND_URL)"
[[ "$frontend" == "https://$domain" ]] || fail "Google OAuth frontend URL must use the production HTTPS origin"

for key in LLM_API_KEY TAVILY_API_KEY ELEVENLABS_API_KEY ELEVENLABS_VOICE_ID OPENAI_API_KEY; do
  required "$key" >/dev/null
done

echo "Production environment checks passed (secret values were not printed)."
docker compose -f deploy/compose.production.yml --env-file "$ENV_FILE" config --quiet
echo "Production Compose configuration is valid."
