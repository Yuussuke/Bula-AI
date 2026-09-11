import hashlib

import httpx
import pytest

from app.modules.auth.password_breach import PasswordBreachChecker


def build_password_hash(password: str) -> str:
    return (
        hashlib.sha1(
            password.encode("utf-8"),
            usedforsecurity=False,
        )
        .hexdigest()
        .upper()
    )


@pytest.mark.anyio
async def test_checker_finds_compromised_password_without_sending_full_hash() -> None:
    password = "senha conhecida"
    password_hash = build_password_hash(password)
    requested_urls: list[str] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        assert request.headers["Add-Padding"] == "true"
        assert request.headers["User-Agent"] == "BulaAI-Password-Breach-Check"
        return httpx.Response(
            status_code=200,
            text=f"{'0' * 35}:0\r\n{password_hash[5:]}:42\r\n",
        )

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        checker = PasswordBreachChecker(
            is_enabled=True,
            timeout_seconds=2,
            http_client=http_client,
        )

        is_compromised = await checker.is_password_compromised(password)

    assert is_compromised is True
    assert requested_urls == [
        f"https://api.pwnedpasswords.com/range/{password_hash[:5]}"
    ]
    assert password not in requested_urls[0]
    assert password_hash not in requested_urls[0]


@pytest.mark.anyio
async def test_checker_accepts_password_absent_from_breach_response() -> None:
    def handle_request(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(status_code=200, text=f"{'0' * 35}:5\r\n")

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        checker = PasswordBreachChecker(
            is_enabled=True,
            timeout_seconds=2,
            http_client=http_client,
        )

        is_compromised = await checker.is_password_compromised("senha inédita")

    assert is_compromised is False


@pytest.mark.anyio
async def test_checker_ignores_padded_match_with_zero_occurrences() -> None:
    password = "senha acolchoada"
    password_hash = build_password_hash(password)

    def handle_request(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(status_code=200, text=f"{password_hash[5:]}:0\r\n")

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        checker = PasswordBreachChecker(
            is_enabled=True,
            timeout_seconds=2,
            http_client=http_client,
        )

        is_compromised = await checker.is_password_compromised(password)

    assert is_compromised is False


@pytest.mark.anyio
async def test_checker_fails_open_when_service_is_unavailable() -> None:
    def handle_request(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Service unavailable", request=request)

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        checker = PasswordBreachChecker(
            is_enabled=True,
            timeout_seconds=2,
            http_client=http_client,
        )

        is_compromised = await checker.is_password_compromised("senha temporária")

    assert is_compromised is False


@pytest.mark.anyio
async def test_checker_fails_open_when_service_response_is_malformed() -> None:
    def handle_request(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(status_code=200, text="unexpected response")

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        checker = PasswordBreachChecker(
            is_enabled=True,
            timeout_seconds=2,
            http_client=http_client,
        )

        is_compromised = await checker.is_password_compromised("senha temporária")

    assert is_compromised is False


@pytest.mark.anyio
async def test_disabled_checker_does_not_make_a_request() -> None:
    def handle_request(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"Unexpected request: {request.url}")

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        checker = PasswordBreachChecker(
            is_enabled=False,
            timeout_seconds=2,
            http_client=http_client,
        )

        is_compromised = await checker.is_password_compromised("qualquer senha")

    assert is_compromised is False
