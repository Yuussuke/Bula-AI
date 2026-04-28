FROM postgres:18 AS builder

ARG PG_MAJOR=18
ARG PGVECTOR_VERSION=v0.8.2
ARG PGVECTORSCALE_VERSION=0.9.0
ARG PG_TEXTSEARCH_VERSION=v1.1.0

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    git \
    jq \
    libssl-dev \
    pkg-config \
    postgresql-server-dev-${PG_MAJOR} \
    && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

RUN cd /tmp \
    && git clone --branch ${PGVECTOR_VERSION} --depth 1 https://github.com/pgvector/pgvector.git \
    && cd pgvector \
    && make \
    && make install

RUN cd /tmp \
    && git clone --branch ${PGVECTORSCALE_VERSION} --depth 1 https://github.com/timescale/pgvectorscale.git \
    && cd pgvectorscale/pgvectorscale \
    && cargo install --locked cargo-pgrx --version "$(cargo metadata --format-version 1 | jq -r '.packages[] | select(.name == "pgrx") | .version')" \
    && cargo pgrx init --pg${PG_MAJOR} /usr/bin/pg_config \
    && cargo pgrx install --release

RUN cd /tmp \
    && git clone --branch ${PG_TEXTSEARCH_VERSION} --depth 1 https://github.com/timescale/pg_textsearch.git \
    && cd pg_textsearch \
    && make \
    && make install

FROM postgres:18

ARG PG_MAJOR=18

LABEL org.opencontainers.image.title="bula_ai_postgres"
LABEL org.opencontainers.image.description="First-party PostgreSQL image for Bula AI with pgvector, pgvectorscale, and pg_textsearch support."
LABEL org.opencontainers.image.source="https://github.com/Yuussuke/Bula-AI"

COPY --from=builder /usr/share/postgresql/${PG_MAJOR}/extension/vector--*.sql /usr/share/postgresql/${PG_MAJOR}/extension/
COPY --from=builder /usr/share/postgresql/${PG_MAJOR}/extension/vector.control /usr/share/postgresql/${PG_MAJOR}/extension/
COPY --from=builder /usr/lib/postgresql/${PG_MAJOR}/lib/vector.so /usr/lib/postgresql/${PG_MAJOR}/lib/

COPY --from=builder /usr/share/postgresql/${PG_MAJOR}/extension/vectorscale--*.sql /usr/share/postgresql/${PG_MAJOR}/extension/
COPY --from=builder /usr/share/postgresql/${PG_MAJOR}/extension/vectorscale.control /usr/share/postgresql/${PG_MAJOR}/extension/
COPY --from=builder /usr/lib/postgresql/${PG_MAJOR}/lib/vectorscale*.so /usr/lib/postgresql/${PG_MAJOR}/lib/

COPY --from=builder /usr/share/postgresql/${PG_MAJOR}/extension/pg_textsearch--*.sql /usr/share/postgresql/${PG_MAJOR}/extension/
COPY --from=builder /usr/share/postgresql/${PG_MAJOR}/extension/pg_textsearch.control /usr/share/postgresql/${PG_MAJOR}/extension/
COPY --from=builder /usr/lib/postgresql/${PG_MAJOR}/lib/pg_textsearch*.so /usr/lib/postgresql/${PG_MAJOR}/lib/

RUN echo "shared_preload_libraries = 'pg_textsearch'" >> /usr/share/postgresql/${PG_MAJOR}/postgresql.conf.sample

COPY --chmod=644 init-extensions.sql /docker-entrypoint-initdb.d/
COPY --chmod=755 verify-image.sh /usr/local/bin/verify-postgres-image

RUN sed -i 's/\r$//' /usr/local/bin/verify-postgres-image

RUN test -f /usr/share/postgresql/${PG_MAJOR}/extension/vector.control \
    && test -f /usr/share/postgresql/${PG_MAJOR}/extension/vectorscale.control \
    && test -f /usr/share/postgresql/${PG_MAJOR}/extension/pg_textsearch.control \
    && test -f /usr/share/postgresql/${PG_MAJOR}/extension/unaccent.control \
    && grep -q "shared_preload_libraries = 'pg_textsearch'" /usr/share/postgresql/${PG_MAJOR}/postgresql.conf.sample \
    && /usr/lib/postgresql/${PG_MAJOR}/bin/postgres --version
