
## AGENTS.md — Bula AI Developer Guide for AI Assistants

> **Who this file is for:** This file guides any AI coding assistant (Copilot, Cursor, Claude, etc.) helping develop the Bula AI project. Read this fully before writing, suggesting, or modifying any code. These rules are non-negotiable and override any "clever" shortcut the AI might prefer.

---

## Project Overview

**Bula AI** is a RAG-powered medication assistant for Brazilian patients. It answers questions about drug leaflets (bulas) using retrieved content from ingested PDFs — never from model hallucination. The backend is a Python FastAPI service, the frontend is React + TypeScript, and the AI pipeline uses LangChain with the Maritaca/Sabiá API and Qdrant for vector search.

**Developer context:** The person using this AI assistant is finishing a Computer Science graduation and is working part-time on this project. They are learning. Explanations matter. Code must be readable. Shortcuts that "work but you'll figure it out later" are not acceptable.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Monorepo layout** | `/backend`, `/frontend`, `/infra` at repo root |
| **Backend language** | Python 3.12 |
| **Backend framework** | FastAPI (async) |
| **ORM** | SQLAlchemy 2 async + Alembic for migrations |
| **Data validation** | Pydantic v2 |
| **Auth** | JWT (PyJWT + Argon2id) |
| **Relational DB** | PostgreSQL 16 |
| **Vector DB** | Qdrant |
| **LLM** | Maritaca Sabiá-3 API (OpenAI-compatible) |
| **Embeddings** | HuggingFace `intfloat/multilingual-e5-large` |
| **RAG framework** | LangChain (LCEL-based chains) |
| **Retrieval** | Dense (Qdrant), BM25, Hybrid (EnsembleRetriever + RRF) |
| **Package manager** | `uv` (not pip, not poetry) |
| **Frontend framework** | React + Vite (TypeScript) |
| **Frontend styling** | Tailwind CSS |
| **HTTP client (frontend)** | Axios + TanStack Query |
| **Containerization** | Docker + Docker Compose (local dev) |
| **CI/CD** | GitHub Actions |
| **Deployment** | Railway (backend + DB), Vercel (frontend) |
| **Testing** | pytest + pytest-asyncio + anyio |

---

## Repository Structure

The project is a **monorepo**. Everything lives inside a single `Bula AI/` repository:

```
Bula AI/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory (create_app function)
│   │   ├── core/                    # Shared kernel — config, DB, security, DI
│   │   │   ├── config.py            # Pydantic Settings (reads from .env)
│   │   │   ├── database.py          # Async SQLAlchemy engine + session factory
│   │   │   ├── security.py          # JWT + password hashing utilities
│   │   │   └── deps.py              # FastAPI Depends() functions live here
│   │   └── modules/
│   │       ├── auth/                # Domain: user registration and login
│   │       ├── bulas/               # Domain: PDF upload and bula metadata
│   │       ├── rag/                 # Domain: ingestion pipeline and retrieval
│   │       └── chat/                # Domain: Q&A sessions and history
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── alembic/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── pages/
│       ├── components/
│       ├── api/
│       └── store/
└── infra/
    └── (Railway configs, GitHub Actions workflows)
```

**Rule:** Never flatten this structure. Never put all models in a single `models.py` at the root. Each module owns its own `models.py`, `schemas.py`, `repository.py`, `service.py`, and `router.py`.

---

## Architecture Rules (Read Carefully)

### Modular Monolith

The backend is a **modular monolith**, not a flat collection of files and not microservices. Code is organized by **domain** (auth, bulas, rag, chat), not by technical type.

Each module follows this strict **layered architecture**:

```
router.py        → HTTP only. Receives request, calls service, returns response.
service.py       → Business logic only. Calls repositories and other services.
repository.py    → Database queries only. No business logic. No HTTP concepts.
schemas.py       → Pydantic models for request/response validation.
models.py        → SQLAlchemy ORM models.
```

**The one rule that must never break:**
> Routers call services. Services call repositories. Repositories talk to the database. **Nothing else does.** A router never touches the database directly. A repository never makes an HTTP call. A service never imports from a router.

### Object-Oriented Python

Prefer classes over standalone functions whenever there is shared state or related behavior.

**Do this:**
```python
class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str, full_name: str) -> User:
        user = User(email=email, hashed_password=hashed_password, full_name=full_name)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
```

**Not this:**
```python
# Bad: loose functions with db passed everywhere
async def get_user_by_email(db, email):
    ...

async def create_user(db, email, hashed_password):
    ...
```

Services and repositories should always be classes. Utilities in `core/` can be standalone functions.

### FastAPI Dependency Injection

**Always use FastAPI's `Depends()` system.** Never instantiate services or repositories directly inside route handlers. Never import `settings` or create a DB session manually inside a route.

```python
# core/deps.py — define all shared dependencies here

async def get_db(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    return session

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    ...
```

```python
# modules/auth/router.py — inject via Depends(), never instantiate manually

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    return await service.register(payload)
```

If you find yourself writing `db = AsyncSessionLocal()` inside a route, stop — that is wrong.

---

## Code Style Rules

### Clarity Over Cleverness

Write the most readable version of the code, even if a shorter or "smarter" version exists. This codebase is also a learning resource.

**Do this:**
```python
async def login(self, payload: LoginRequest) -> TokenResponse:
    user = await self.repo.get_by_email(payload.email)

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    password_is_valid = verify_password(payload.password, user.hashed_password)
    if not password_is_valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user_id=user.id)
    return TokenResponse(access_token=token, token_type="bearer")
```

**Not this:**
```python
async def login(self, payload: LoginRequest) -> TokenResponse:
    user = await self.repo.get_by_email(payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id), token_type="bearer")
```

The second version is shorter but harder to debug and harder to read. Always prefer the first style.

### Naming

- Use long, descriptive variable names. `user_with_matching_email` is better than `u`.
- Function names should read like sentences: `get_bula_by_id`, `create_chat_session`, `build_hybrid_retriever`.
- Boolean variables should start with `is_`, `has_`, or `can_`: `is_active`, `has_permission`.

### Type Hints

Every function must have full type hints — parameters and return types. No exceptions.

```python
# Good
async def get_by_id(self, user_id: str) -> User | None:

# Bad
async def get_by_id(self, user_id):
```

### Pydantic Schemas

All incoming request data must go through a Pydantic schema. All outgoing response data must go through a Pydantic schema. Never return raw SQLAlchemy model objects from endpoints.

---

## Testing Rules

### What to Test

Write tests that verify **behavior**, not implementation. A test should tell you *what the code does*, not *how it does it*.

**Good test:** Does the login endpoint return a JWT token when given valid credentials?
**Bad test:** Does the login function call `verify_password` once?

If deleting a test would make you less confident the feature works, it is a good test. If you could delete the implementation and the test would still pass, it is a useless test.

### Unit Tests

Unit tests live in `tests/unit/`. They test a single class or function in isolation. Use mocks only when you need to replace an external dependency (database, HTTP call). Never mock the thing you are testing.

```python
# tests/unit/test_security.py
from app.core.security import hash_password, verify_password

def test_password_round_trip():
    plain = "my_secure_password"
    hashed = hash_password(plain)

    assert hashed != plain
    assert verify_password(plain, hashed) is True

def test_wrong_password_does_not_verify():
    hashed = hash_password("correct_password")
    assert verify_password("wrong_password", hashed) is False
```

### Integration Tests

Integration tests live in `tests/integration/`. Use them for the **complex, important paths** of the application: auth flows, the full RAG pipeline, file ingestion. Do not write integration tests for every endpoint.

Integration tests use a real test database. Use `pytest` fixtures to create and tear down test data.

```python
# tests/integration/test_auth.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.anyio
async def test_register_creates_user_and_returns_201():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json={
            "email": "test@Bula AI.com",
            "password": "secret123",
            "full_name": "Test User",
        })

    assert response.status_code == 201
    assert response.json()["email"] == "test@Bula AI.com"

@pytest.mark.anyio
async def test_login_with_valid_credentials_returns_token():
    # ... first register, then login
    ...
    assert "access_token" in response.json()
```

### What NOT to Test

- Do not test that Pydantic validation works (that is Pydantic's job to test).
- Do not test SQLAlchemy internals.
- Do not write a test that just calls a function and asserts it does not throw an error with no meaningful assertion.

---

## Database Rules

### Always Use Alembic for Schema Changes

Never use `Base.metadata.create_all()` to create tables in production or staging. All schema changes must go through an Alembic migration:

```bash
alembic revision --autogenerate -m "describe what changed"
alembic upgrade head
```

### Async Sessions

Always use `async with AsyncSessionLocal() as session` via the `get_session` dependency. Never create a raw synchronous session.

### No Raw SQL

Use SQLAlchemy ORM or Core constructs. No raw SQL strings via `text()` unless there is a documented reason.

---

## Error Handling

### HTTP Errors Use HTTPException

```python
from fastapi import HTTPException, status

# Good
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Bula not found",
)

# Bad — never use generic Exception for HTTP errors
raise Exception("not found")
```

### Unexpected Errors Have a Global Handler

The global exception handler in `core/exceptions.py` catches unhandled exceptions and returns a safe JSON response. It logs the error internally but never exposes stack traces to the client.

### Fail Early, Fail Clearly

Check for errors at the top of a function and return/raise immediately. Avoid deeply nested `if/else` trees.

```python
# Good — early returns
async def get_bula_for_user(self, bula_id: str, user_id: str) -> Bula:
    bula = await self.repo.get_by_id(bula_id)
    if bula is None:
        raise HTTPException(status_code=404, detail="Bula not found")

    if bula.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this bula")

    return bula
```

---

## Security Rules

These must never be skipped:

- **Passwords** are always hashed with Argon2id (via pwdlib) before storing. Never store or log a plain-text password.
- **JWT tokens** are validated on every protected request via the `get_current_user` dependency.
- **File uploads** are validated: only `application/pdf` is accepted, maximum 10MB.
- **Environment variables** hold all secrets. Nothing secret is hardcoded. The `.env` file is never committed to git.
- **CORS** is restricted to known frontend origins. The wildcard `*` is never used in production.

---

## Dependency Update Automation (Dependabot)

The repository uses Dependabot for automated dependency maintenance. The source of truth is `.github/dependabot.yml`.

Current required ecosystems:

- `uv` in `/backend` (Python dependencies and `uv.lock` updates)
- `npm` in `/frontend` (frontend dependencies and lockfile updates)
- `docker` in `/backend` (backend base image updates)
- `docker` in `/frontend` (kept ready for future `frontend/Dockerfile`)
- `docker` in `/` (root `docker-compose.yml` image updates)
- `github-actions` in `/` (workflow action version updates)

Rules for assistants and maintainers:

- Keep update schedules weekly unless explicitly changed by maintainers.
- Keep labels and reviewer assignment aligned with repository policy.
- Keep `uv` and `npm` updates grouped: one group for minor/patch and one group for major.
- Treat major runtime/image upgrades (for example Python and PostgreSQL) as manual-review updates that require compatibility testing.
- Do not remove the `/frontend` Docker entry just because `frontend/Dockerfile` is not present yet; it is intentionally pre-configured.

---

## What to Do When Unsure

If a task is ambiguous or could be done in more than one way, **ask before writing code**. It is better to spend 2 minutes clarifying than 2 hours refactoring.

If you are about to do something that violates a rule in this document, **stop and say so**. Do not silently work around the rules.

If you are adding a new module or new feature that is not covered by the development plan document, **say that explicitly** and describe what you are adding before writing the code.

---

## Quick Reference: The Rules in One Place

| Topic | Rule |
|---|---|
| Module structure | One folder per domain. Each has router, service, repository, schemas, models. |
| Layering | Routers → Services → Repositories → Database. Never skip a layer. |
| OOP | Services and repositories are always classes, not loose functions. |
| DI | Always use `Depends()`. Never instantiate dependencies manually inside routes. |
| Typing | Every function has full type hints. |
| Tests | Test behavior, not implementation. Unit tests for logic, integration for complex flows. |
| Tests (anti-pattern) | No tests that just mirror the implementation. |
| DB changes | Always use Alembic migrations. Never `create_all()` in production. |
| Security | Hash passwords. Validate JWTs. Validate file types. Never commit secrets. |
| Dependency updates | Keep `.github/dependabot.yml` aligned with all active ecosystems and lockfiles. |
| Code style | Readable over clever. Verbose over terse. Long names over short names. |
| Git | Small PRs. Descriptive commit messages. Never push directly to `main`. |

```
