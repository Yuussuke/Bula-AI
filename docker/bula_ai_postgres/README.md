# Bula AI PostgreSQL Image

This directory defines the first-party PostgreSQL image for Bula AI.

The image is intentionally thin. Its main purpose is to give the project one
auditable database artifact for local development, CI, and future deployment
parity while keeping the database image lifecycle separate from application
releases.

## Image contract

- Local image name: `bula_ai_postgres:0.8.1-pg16`
- GHCR image: `ghcr.io/yuussuke/bula_ai_postgres:0.8.1-pg16`
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

The publish workflow builds this image on pull requests and pushes it to GHCR on
`main` and `workflow_dispatch`.

The workflow uses the repository `GITHUB_TOKEN` with `packages: write` to publish
the package. Package visibility is a repository policy decision:

- Public package: local development and future CI consumers can pull the image
  without a `docker login`.
- Private package: local development and future CI consumers must authenticate
  with `docker login ghcr.io` before pulling the image.

After the first successful publish, confirm the package visibility in GitHub's
package settings before switching `docker-compose.yml` or CI service containers
to the GHCR image.
