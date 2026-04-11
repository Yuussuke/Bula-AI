# Backend Setup Notes

This backend uses Alembic + SQLAlchemy async with PostgreSQL.

## 1) Environment variables

Provide the required environment variables for Docker Compose.

This project is Docker-first:

- `DATABASE_URL` is injected into the `api` container by Docker Compose.
- `SECRET_KEY` must be provided via your `.env` file (see `.env.example`).

## 2) Migrations (recommended flow)

Run migrations from container to avoid host/DNS mismatches:

```bash
make up
make migrate

# Option A (interactive):
make makemigrations

# Option B (non-interactive):
MSG="your_message" make makemigrations
```

## 3) Common DNS error

If you get `socket.gaierror: [Errno 11001] getaddrinfo failed`,
the hostname in `DATABASE_URL` is not resolvable in the current execution context.

This usually happens when running commands outside Docker while using the Docker-only hostname `postgres`.

- Recommended fix: run migrations via `make migrate` / `make makemigrations` (inside the container).
