# Backend Setup Notes

This backend uses Alembic + SQLAlchemy async with PostgreSQL.

## 1) Environment variables

Provide the required environment variables for Docker Compose.

This project is Docker-first:

- `DATABASE_URL` is injected into the `api` container by Docker Compose.
- `SECRET_KEY` must be provided via your `.env` file (see `.env.example`).
- The local PostgreSQL service uses `ghcr.io/yuussuke/bula_ai_postgres:0.8.1-pg16`.
  If the GHCR package is private, authenticate with `docker login ghcr.io`
  before starting the stack.

## 2) Migrations (recommended flow)

Run migrations from container to avoid host/DNS mismatches:

```bash
make up
make verify-postgres
make migrate

# Option A (interactive):
make makemigrations

# Option B (non-interactive):
MSG="your_message" make makemigrations
```

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

The project uses a first-party PostgreSQL 16 image with pgvector and PostgreSQL
full-text-search support. Verify the running database with:

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
`bula-ai_postgres_data`.
