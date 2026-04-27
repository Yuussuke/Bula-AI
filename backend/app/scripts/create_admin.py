from __future__ import annotations

import argparse
import asyncio
import getpass
import os
from collections.abc import Sequence

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory, close_engine
from app.modules.auth.repository import RefreshTokenRepository, UserRepository
from app.modules.auth.schemas import UserCreate
from app.modules.auth.security import PasswordHasher
from app.modules.auth.service import AuthService, TokenService, UserAlreadyExistsError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create an administrator user for Bula AI."
    )
    parser.add_argument("--email", help="Admin email address.")
    parser.add_argument("--full-name", help="Admin full name.")
    return parser


def prompt_required_text(value: str | None, prompt: str) -> str:
    if value is not None and value.strip():
        return value.strip()

    return input(prompt).strip()


def prompt_admin_password() -> str:
    password_from_environment = os.getenv("ADMIN_PASSWORD")
    if password_from_environment:
        return password_from_environment

    password = getpass.getpass("Admin password: ")
    password_confirmation = getpass.getpass("Confirm admin password: ")

    if password != password_confirmation:
        raise ValueError("Passwords do not match.")

    return password


def build_auth_service(db: AsyncSession) -> AuthService:
    return AuthService(
        user_repository=UserRepository(db=db),
        refresh_token_repository=RefreshTokenRepository(db=db),
        password_hasher=PasswordHasher(),
        token_service=TokenService(
            secret_key=settings.secret_key,
            algorithm=settings.algorithm,
            access_token_expire_minutes=settings.access_token_expire_minutes,
        ),
    )


async def create_admin_user(email: str, full_name: str, password: str) -> None:
    admin_user_input = UserCreate(
        email=email,
        full_name=full_name,
        password=password,
    )

    async with async_session_factory() as session:
        auth_service = build_auth_service(session)
        admin_user = await auth_service.create_admin_user(admin_user_input)

    print(
        f"Admin user created successfully: id={admin_user.id}, email={admin_user.email}"
    )


async def async_main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        email = prompt_required_text(args.email, "Admin email: ")
        full_name = prompt_required_text(args.full_name, "Admin full name: ")
        password = prompt_admin_password()

        await create_admin_user(email=email, full_name=full_name, password=password)
    except ValidationError:
        print("Invalid admin data. Check email, full name, and password policy.")
        return 1
    except UserAlreadyExistsError:
        print("A user with this email already exists.")
        return 1
    except ValueError as exc:
        print(str(exc))
        return 1
    finally:
        await close_engine()

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
