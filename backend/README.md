# Backend Setup Notes

This backend uses Alembic + SQLAlchemy async with PostgreSQL.

## 1) Environment variables

Provide the required environment variables for Docker Compose.

This project is Docker-first:

- `DATABASE_URL` is injected into the `api` container by Docker Compose.
- `SECRET_KEY` must be provided via your `.env` file (see `.env.example`).
- The local PostgreSQL service uses `ghcr.io/yuussuke/bula_ai_postgres:18`.
  If the GHCR package is private, authenticate with `docker login ghcr.io`
  before starting the stack.

## 2) Migrations (recommended flow)

Run migrations from container to avoid host/DNS mismatches:

```bash
make up
make verify-postgres
make migrate
make pgq-install

# Option A (interactive):
make makemigrations

# Option B (non-interactive):
MSG="your_message" make makemigrations
```

PGQueuer owns its own queue tables. Use `make pgq-install` on a fresh database,
`make pgq-upgrade` during deploys, and `make pgq-verify` when checking the
queue schema.

## 3) Management commands

Create administrators from inside the Docker workflow:

```bash
make create-admin ARGS="--email admin@example.com --full-name 'Admin User'"
```

The command prompts for the password securely. For non-interactive environments,
set `ADMIN_PASSWORD` before running the make target. Public self-registration
never accepts a role and always creates `user` accounts.

## 4) Common DNS error

If you get `socket.gaierror: [Errno 11001] getaddrinfo failed`,
the hostname in `DATABASE_URL` is not resolvable in the current execution context.

This usually happens when running commands outside Docker while using the Docker-only hostname `postgres`.

- Recommended fix: run migrations via `make migrate` / `make makemigrations` (inside the container).

## 5) PostgreSQL image and local reset

The project uses a first-party PostgreSQL 18 image with pgvector, pgvectorscale,
pg_textsearch, and PostgreSQL full-text-search support. Verify the running
database with:

```bash
make verify-postgres
```

When switching database image tags, use the Docker-first reset flow:

```bash
make reset-db
```

This removes the local Compose database volume and reruns migrations, so it is
destructive for local data. The volume is declared as `postgres_data` in
`docker-compose.yml` and is usually materialized by Docker as
`bula-ai_postgres_data`. PostgreSQL 18 mounts it at `/var/lib/postgresql` so the
image can create its major-version-specific data directory.

## 6) RAG evidence selector model

The default `MARITACA_MODEL` is `sabia-4`. An explicitly configured environment
value still overrides this default. This setting applies to the chat LLM, not
only to evidence selection; restart the API after changing the environment.

The choice followed an auxiliary evaluation of the evidence selector using 12
frozen cases (nine positive and three negative), three repetitions per model,
the same evidence units, prompt, structured output, temperature 0.2, and
alternating model order. Repetitions are not independent test cases.

| Comparison | Model | Negative errors | Calls with tangential evidence | Positive coverage |
| --- | --- | ---: | ---: | ---: |
| Original model comparison | `sabiazinho-4` | 3/9 | 6/36 | 27/27 |
| Original model comparison | `sabia-4` | 0/9 | 0/36 | 27/27 |
| Later Thinking comparison | `sabia-4` | 0/9 | 3/36 | 27/27 |
| Later Thinking comparison | `sabia-4-thinking` | 1/9 | 2/36 | 27/27 |

The paraphrase check kept adequate selection in all 12 paired cases; 11 pairs
selected identical ID sets. There were no false abstentions or technical
failures in these comparisons. Thinking averaged 4.60 seconds per selection
versus 0.90 seconds for `sabia-4` in the later comparison. The remaining
tangential-selection case and qualification differences still require
full-pipeline review. This small benchmark supports the default change; it
does not establish generalization to other leaflets or clinical safety. Raw
experimental outputs and benchmark-only scripts are not part of production.
