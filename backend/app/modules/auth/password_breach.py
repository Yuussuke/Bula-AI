import hashlib

import httpx
import structlog

logger = structlog.get_logger(__name__)

PWNED_PASSWORDS_RANGE_URL = "https://api.pwnedpasswords.com/range"
PWNED_PASSWORDS_USER_AGENT = "BulaAI-Password-Breach-Check"


class InvalidPasswordBreachResponseError(Exception):
    """Raised when the breach service returns an unexpected response body."""


class PasswordBreachChecker:
    """Checks passwords against Pwned Passwords without disclosing the password."""

    def __init__(
        self,
        *,
        is_enabled: bool,
        timeout_seconds: float,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.is_enabled = is_enabled
        self.timeout_seconds = timeout_seconds
        self.http_client = http_client

    async def is_password_compromised(self, password: str) -> bool:
        if not self.is_enabled:
            return False

        password_hash = (
            hashlib.sha1(
                password.encode("utf-8"),
                usedforsecurity=False,
            )
            .hexdigest()
            .upper()
        )
        hash_prefix = password_hash[:5]
        hash_suffix = password_hash[5:]

        try:
            response_body = await self._request_hash_range(hash_prefix)
            return self._response_contains_hash_suffix(
                response_body=response_body,
                expected_hash_suffix=hash_suffix,
            )
        except (httpx.HTTPError, InvalidPasswordBreachResponseError) as exc:
            logger.warning(
                "password_breach_check_unavailable",
                reason=type(exc).__name__,
            )
            return False

    async def _request_hash_range(self, hash_prefix: str) -> str:
        if self.http_client is not None:
            return await self._execute_request(
                http_client=self.http_client,
                hash_prefix=hash_prefix,
            )

        async with httpx.AsyncClient() as http_client:
            return await self._execute_request(
                http_client=http_client,
                hash_prefix=hash_prefix,
            )

    async def _execute_request(
        self,
        *,
        http_client: httpx.AsyncClient,
        hash_prefix: str,
    ) -> str:
        response = await http_client.get(
            f"{PWNED_PASSWORDS_RANGE_URL}/{hash_prefix}",
            headers={
                "Add-Padding": "true",
                "User-Agent": PWNED_PASSWORDS_USER_AGENT,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.text

    def _response_contains_hash_suffix(
        self,
        *,
        response_body: str,
        expected_hash_suffix: str,
    ) -> bool:
        for response_line in response_body.splitlines():
            if not response_line:
                continue

            hash_suffix, separator, occurrence_count_text = response_line.partition(":")
            if not separator:
                raise InvalidPasswordBreachResponseError()

            normalized_hash_suffix = hash_suffix.strip().upper()
            try:
                occurrence_count = int(occurrence_count_text.strip())
            except ValueError as exc:
                raise InvalidPasswordBreachResponseError() from exc

            if normalized_hash_suffix == expected_hash_suffix:
                return occurrence_count > 0

        return False
