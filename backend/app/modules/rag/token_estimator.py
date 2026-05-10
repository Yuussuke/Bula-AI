from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import tiktoken

from app.core.config import Settings


class TokenEstimator(Protocol):
    def estimate(self, text: str) -> int:
        """Estimate token count for chunk bounds and metadata."""


@dataclass(frozen=True)
class HeuristicTokenEstimator:
    def estimate(self, text: str) -> int:
        # Intentional fallback for offline tests and unavailable tokenizers.
        # This is approximate and should not be treated as provider-exact.
        return max(1, len(text) // 4)


@dataclass(frozen=True)
class TiktokenTokenEstimator:
    encoding_name: str
    _encoding: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_encoding",
            tiktoken.get_encoding(self.encoding_name),
        )

    def estimate(self, text: str) -> int:
        return max(1, len(self._encoding.encode(text)))


def build_token_estimator(*, settings: Settings) -> TokenEstimator:
    encoding_name = (settings.processing.tokenizer_encoding or "").strip()
    if not encoding_name:
        return HeuristicTokenEstimator()

    try:
        return TiktokenTokenEstimator(encoding_name=encoding_name)
    except Exception:
        return HeuristicTokenEstimator()
