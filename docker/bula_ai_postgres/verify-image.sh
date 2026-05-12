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

echo "Waiting for bundled extensions..."
extension_attempts=0
until extension_count="$(
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At \
        -c "SELECT count(*) FROM pg_extension WHERE extname IN ('vector', 'vectorscale', 'pg_textsearch', 'unaccent');" \
        2>/dev/null
)" && [ "$extension_count" = "4" ]; do
    if ! kill -0 "$postgres_pid" >/dev/null 2>&1; then
        wait "$postgres_pid"
        exit 1
    fi

    extension_attempts=$((extension_attempts + 1))
    if [ "$extension_attempts" -ge 60 ]; then
        echo "Timed out waiting for PostgreSQL extensions." >&2
        exit 1
    fi

    sleep 1
done

psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
    -c "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'vectorscale', 'pg_textsearch', 'unaccent') ORDER BY extname;" \
    -c "SELECT to_tsvector('portuguese', unaccent(U&'contraindica\00E7\00E3o')) AS portuguese_fts_probe;"
