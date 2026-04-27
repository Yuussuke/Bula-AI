# Bula AI PostgreSQL Image

This directory defines the first-party PostgreSQL image for Bula AI.

The image is intentionally thin. Its main purpose is to give the project one
auditable database artifact for local development, CI, and future deployment
parity while keeping the database image lifecycle separate from application
releases.

## Image contract

- Local image name: `bula_ai_postgres:0.8.1-pg16`
- Planned GHCR image: `ghcr.io/yuussuke/bula_ai_postgres:0.8.1-pg16`
- Base image: `pgvector/pgvector:0.8.1-pg16`
- PostgreSQL major version: 16
- Required PostgreSQL capabilities:
  - `vector` extension from pgvector
  - `unaccent` extension
  - PostgreSQL native full-text search with the `portuguese` configuration

The project image tag mirrors the underlying `FROM` tag. For example, if the
base image becomes `pgvector/pgvector:0.8.2-pg16`, the Bula AI image should be
published as `ghcr.io/yuussuke/bula_ai_postgres:0.8.2-pg16`. This tag is not an
application version.

## Local commands

Build the image:

```bash
make build-postgres-image
```

Run the image verification:

```bash
make verify-postgres-image
```

The verification starts a temporary PostgreSQL container without a named data
volume and runs SQL checks for `vector`, `unaccent`, and Portuguese full-text
search. It does not create the `chunk_meta` schema or implement BM25 retrieval;
that work belongs to issue #32.

## GHCR access policy

Whether the GHCR package is public or private must be decided and documented
when the publish workflow is added. If the package stays private, local
development and CI documentation must include the required `docker login ghcr.io`
step before pulling the image.
