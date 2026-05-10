from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol, cast

import structlog

from app.core.config import Settings


logger = structlog.get_logger(__name__)


class TokenEstimator(Protocol):
    def estimate(self, text: str) -> int:
        """Estimate token count for chunk bounds and metadata."""


class TokenEncoding(Protocol):
    def encode(self, text: str) -> list[int]:
        """Encode text into token ids."""


@dataclass(frozen=True)
class HeuristicTokenEstimator:
    def estimate(self, text: str) -> int:
        # Intentional fallback for offline tests and unavailable tokenizers.
        # This is approximate and should not be treated as provider-exact.
        return max(1, len(text) // 4)


@dataclass(frozen=True)
class TiktokenTokenEstimator:
    encoding_name: str
    _encoding: TokenEncoding = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_encoding",
            _get_tiktoken_encoding(self.encoding_name),
        )

    def estimate(self, text: str) -> int:
        return max(1, len(self._encoding.encode(text)))


def build_token_estimator(*, settings: Settings) -> TokenEstimator:
    encoding_name = (settings.processing.tokenizer_encoding or "").strip()
    if not encoding_name:
        return HeuristicTokenEstimator()

    try:
        return TiktokenTokenEstimator(encoding_name=encoding_name)
    except (ImportError, LookupError, ValueError) as exc:
        logger.warning(
            "rag_token_estimator_fallback",
            encoding_name=encoding_name,
            error_type=exc.__class__.__name__,
        )
        return HeuristicTokenEstimator()


@lru_cache(maxsize=8)
def _get_tiktoken_encoding(encoding_name: str) -> TokenEncoding:
    import tiktoken

    return cast(TokenEncoding, tiktoken.get_encoding(encoding_name))
