# Bula AI PostgreSQL Image

This directory defines the first-party PostgreSQL image for Bula AI.

The image is intentionally first-party. Its main purpose is to give the project
one auditable database artifact for local development, CI, and future deployment
parity while keeping the database image lifecycle separate from application
releases.

## Why first-party GHCR

The `joeychilson/railway-pg-vectorscale-textsearch` project is the design
reference for the pgvector, pgvectorscale, and pg_textsearch direction. Bula AI
uses the same shape of image, but should not depend on pulling that third-party
image directly as its long-term default. Using an in-repository Dockerfile and
publishing `bula_ai_postgres` to GHCR gives the project an explicit, reviewable
update path through Dependabot and CI. It also keeps rebuild cadence,
base-image updates, and local/CI/future production parity under this
repository's control.

## Image contract

- Local image name: `bula_ai_postgres:18`
- GHCR image: `ghcr.io/yuussuke/bula_ai_postgres:18`
- Base image: `postgres:18`
- PostgreSQL major version: 18
- Required PostgreSQL capabilities:
  - `vector` extension from pgvector
  - `vectorscale` extension from pgvectorscale
  - `pg_textsearch` extension for BM25 text search
  - `unaccent` extension
  - PostgreSQL native full-text search with the `portuguese` configuration
- Image default:
  - `shared_preload_libraries = 'pg_textsearch'`

The project image tag mirrors the underlying `FROM` tag. For example, if the
base image becomes `postgres:18.1`, the Bula AI image should be published as
`ghcr.io/yuussuke/bula_ai_postgres:18.1`. This tag is not an application version.

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
volume and runs SQL checks for `vector`, `vectorscale`, `pg_textsearch`,
`unaccent`, and Portuguese full-text search. It does not create the `chunk_meta`
schema or implement BM25 retrieval; that work belongs to issue #32.

## Volume reset when changing image tags

Changing PostgreSQL major versions or database image tags can make an existing
local data volume incompatible with the new server. Prefer doing this early,
before local Phase 3 data grows.

Preferred Docker-first reset:

```bash
make reset-db
```

This removes the Compose-managed PostgreSQL volume, recreates the stack, waits
for PostgreSQL to accept connections, and reruns migrations. It is destructive
for local database data.

The volume is declared in `docker-compose.yml` as `postgres_data`. With the
current Compose project name, Docker usually materializes it as:

```text
bula-ai_postgres_data
```

Fallback inspection command:

```bash
docker volume ls --filter name=postgres_data
```

Fallback manual removal, only after stopping the stack and only when local data
loss is acceptable:

```bash
make down
docker volume rm bula-ai_postgres_data
make up
make migrate
```

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

## Dependency updates

Dependabot monitors this directory as a Docker ecosystem. When the `postgres`
base tag changes, Dependabot should open a reviewable PR against
`docker/bula_ai_postgres/Dockerfile`.

Review database-image update PRs separately from application releases:

- The Bula AI application version does not control this image tag.
- The image tag must continue to mirror the underlying `FROM` tag.
- PostgreSQL, pgvector, pgvectorscale, and pg_textsearch upgrades require manual
  compatibility review before merge.
- After changing the base tag, run `make build-postgres-image` and
  `make verify-postgres-image`.
