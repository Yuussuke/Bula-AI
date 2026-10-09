"""Source structure shared by retrieval eligibility and evidence preparation."""

from enum import StrEnum
import re


# Also used by PostgreSQL's advanced regular-expression engine. No source
# headings or drug-specific vocabulary determine a chunk's structural role.
FRONT_MATTER_PREFIX_PATTERN = r"\A[\ufeff \t\r\n]*---[ \t]*\r?\n"
FRONT_MATTER_ENVELOPE_PATTERN = (
    FRONT_MATTER_PREFIX_PATTERN
    + r"(?:[^\r\n]*\r?\n)*?[ \t]*(?:---|\.\.\.)[ \t]*(?:\r?\n|$)"
)
FRONT_MATTER_PREFIX = re.compile(FRONT_MATTER_PREFIX_PATTERN)
FRONT_MATTER_ENVELOPE = re.compile(FRONT_MATTER_ENVELOPE_PATTERN, re.DOTALL)


class ChunkContentRole(StrEnum):
    DOCUMENT_METADATA = "document_metadata"
    EVIDENCE = "evidence"


def without_front_matter(source_text: str) -> str:
    if FRONT_MATTER_PREFIX.match(source_text) is None:
        return source_text
    envelope = FRONT_MATTER_ENVELOPE.match(source_text)
    # Fail closed for an unterminated envelope, as evidence preparation does.
    return source_text[envelope.end() :] if envelope is not None else ""


def classify_chunk_content(source_text: str) -> ChunkContentRole:
    if (
        FRONT_MATTER_PREFIX.match(source_text) is not None
        and not without_front_matter(source_text).strip()
    ):
        return ChunkContentRole.DOCUMENT_METADATA
    return ChunkContentRole.EVIDENCE
