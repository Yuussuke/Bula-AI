FROM pgvector/pgvector:0.8.1-pg16

LABEL org.opencontainers.image.title="bula_ai_postgres"
LABEL org.opencontainers.image.description="First-party PostgreSQL image for Bula AI with pgvector and PostgreSQL full-text search support."
LABEL org.opencontainers.image.source="https://github.com/Yuussuke/Bula-AI"

RUN test -f /usr/share/postgresql/16/extension/vector.control \
    && test -f /usr/share/postgresql/16/extension/unaccent.control \
    && /usr/lib/postgresql/16/bin/postgres --version
