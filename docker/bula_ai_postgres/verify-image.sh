#!/usr/bin/env sh
set -eu

docker-entrypoint.sh postgres &
postgres_pid="$!"

cleanup() {
    kill "$postgres_pid" >/dev/null 2>&1 || true
    wait "$postgres_pid" >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

echo "Waiting for temporary PostgreSQL container..."
until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
    sleep 1
done

psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
    -c "CREATE EXTENSION IF NOT EXISTS vector;" \
    -c "CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;" \
    -c "CREATE EXTENSION IF NOT EXISTS pg_textsearch;" \
    -c "CREATE EXTENSION IF NOT EXISTS unaccent;" \
    -c "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'vectorscale', 'pg_textsearch', 'unaccent') ORDER BY extname;" \
    -c "SELECT to_tsvector('portuguese', unaccent(U&'contraindica\00E7\00E3o')) AS portuguese_fts_probe;"
