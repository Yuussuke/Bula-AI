from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal, Sequence


ValidationFailureReason = Literal[
    "duplicate_span",
    "empty_chunk",
    "invalid_span",
    "missing_source_text",
    "non_source_text",
    "overlapping_span",
    "reordered_span",
]

SOURCE_TOKEN_PATTERN = re.compile(r"\S+")
MARKDOWN_HEADING_PATTERN = re.compile(
    r"^(?P<marks>#{2,6})\s+(?P<title>.+?)\s*$",
    flags=re.MULTILINE,
)


class SourceChunkValidationError(ValueError):
    """Raised when semantic chunks cannot be reconstructed from their source."""

    def __init__(self, reason: ValidationFailureReason) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class SourceToken:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class SourceChunkSpan:
    text: str
    start: int
    end: int
    chunk_title: str


@dataclass(frozen=True)
class MarkdownHeading:
    level: int
    title: str
    start: int


class SourceHeadingResolver:
    """Derive chunk titles exclusively from validated Markdown source headings."""

    def resolve_title(
        self,
        *,
        source_text: str,
        span_start: int,
        section_title: str,
    ) -> str:
        active_headings: list[MarkdownHeading] = []

        for heading_match in MARKDOWN_HEADING_PATTERN.finditer(source_text):
            if heading_match.start() > span_start:
                break

            heading = MarkdownHeading(
                level=len(heading_match.group("marks")),
                title=heading_match.group("title").strip(),
                start=heading_match.start(),
            )
            active_headings = [
                active_heading
                for active_heading in active_headings
                if active_heading.level < heading.level
            ]
            active_headings.append(heading)

        if active_headings:
            return active_headings[-1].title

        clean_section_title = section_title.strip()
        if clean_section_title:
            return clean_section_title

        return "Documento"


class SourceChunkValidator:
    """Validate complete ordered source coverage and rebuild exact source spans."""

    def __init__(self, heading_resolver: SourceHeadingResolver | None = None) -> None:
        self.heading_resolver = heading_resolver or SourceHeadingResolver()

    def validate_and_reconstruct(
        self,
        *,
        source_text: str,
        proposed_chunk_texts: Sequence[str],
        section_title: str,
    ) -> list[SourceChunkSpan]:
        source_tokens = self._tokenize(source_text)
        if not source_tokens:
            raise SourceChunkValidationError("invalid_span")

        if not proposed_chunk_texts:
            raise SourceChunkValidationError("missing_source_text")

        proposed_token_groups = [
            self._tokenize_proposal(proposed_chunk_text)
            for proposed_chunk_text in proposed_chunk_texts
        ]
        validated_token_ranges: list[tuple[int, int]] = []
        source_cursor = 0

        for proposal_index, proposed_tokens in enumerate(proposed_token_groups):
            proposed_token_texts = [token.text for token in proposed_tokens]
            proposed_token_count = len(proposed_token_texts)
            proposed_end = source_cursor + proposed_token_count
            expected_source_tokens = [
                token.text for token in source_tokens[source_cursor:proposed_end]
            ]

            if proposed_token_texts != expected_source_tokens:
                reason = self._classify_mismatch(
                    source_tokens=source_tokens,
                    source_cursor=source_cursor,
                    proposed_token_texts=proposed_token_texts,
                    remaining_proposals=proposed_token_groups[proposal_index + 1 :],
                )
                raise SourceChunkValidationError(reason)

            validated_token_ranges.append((source_cursor, proposed_end))
            source_cursor = proposed_end

        if source_cursor != len(source_tokens):
            raise SourceChunkValidationError("missing_source_text")

        return self._reconstruct_spans(
            source_text=source_text,
            source_tokens=source_tokens,
            token_ranges=validated_token_ranges,
            section_title=section_title,
        )

    def _tokenize(self, text: str) -> list[SourceToken]:
        return [
            SourceToken(
                text=token_match.group(0),
                start=token_match.start(),
                end=token_match.end(),
            )
            for token_match in SOURCE_TOKEN_PATTERN.finditer(text)
        ]

    def _tokenize_proposal(self, proposed_chunk_text: str) -> list[SourceToken]:
        proposed_tokens = self._tokenize(proposed_chunk_text)
        if not proposed_tokens:
            raise SourceChunkValidationError("empty_chunk")
        return proposed_tokens

    def _classify_mismatch(
        self,
        *,
        source_tokens: Sequence[SourceToken],
        source_cursor: int,
        proposed_token_texts: Sequence[str],
        remaining_proposals: Sequence[Sequence[SourceToken]],
    ) -> ValidationFailureReason:
        source_token_texts = [token.text for token in source_tokens]
        proposal_starts = self._find_token_sequence_starts(
            source_tokens=source_token_texts,
            proposed_tokens=proposed_token_texts,
        )
        if not proposal_starts:
            return "non_source_text"

        proposal_ranges = [
            (proposal_start, proposal_start + len(proposed_token_texts))
            for proposal_start in proposal_starts
        ]
        if any(
            proposal_start < source_cursor < proposal_end
            for proposal_start, proposal_end in proposal_ranges
        ):
            return "overlapping_span"

        if any(proposal_start > source_cursor for proposal_start in proposal_starts):
            expected_source_suffix = source_token_texts[source_cursor:]
            if self._remaining_proposals_start_with_source(
                remaining_proposals=remaining_proposals,
                expected_source_suffix=expected_source_suffix,
            ):
                return "reordered_span"
            return "missing_source_text"

        if any(proposal_end <= source_cursor for _, proposal_end in proposal_ranges):
            return "duplicate_span"

        return "invalid_span"

    def _find_token_sequence_starts(
        self,
        *,
        source_tokens: Sequence[str],
        proposed_tokens: Sequence[str],
    ) -> list[int]:
        if len(proposed_tokens) > len(source_tokens):
            return []

        prefix_lengths = self._build_prefix_lengths(proposed_tokens)
        matched_token_count = 0
        sequence_starts: list[int] = []

        for source_index, source_token in enumerate(source_tokens):
            while (
                matched_token_count > 0
                and source_token != proposed_tokens[matched_token_count]
            ):
                matched_token_count = prefix_lengths[matched_token_count - 1]

            if source_token == proposed_tokens[matched_token_count]:
                matched_token_count += 1

            if matched_token_count == len(proposed_tokens):
                sequence_starts.append(source_index - len(proposed_tokens) + 1)
                matched_token_count = prefix_lengths[matched_token_count - 1]

        return sequence_starts

    def _build_prefix_lengths(self, tokens: Sequence[str]) -> list[int]:
        prefix_lengths = [0] * len(tokens)
        matched_prefix_length = 0

        for token_index in range(1, len(tokens)):
            while (
                matched_prefix_length > 0
                and tokens[token_index] != tokens[matched_prefix_length]
            ):
                matched_prefix_length = prefix_lengths[matched_prefix_length - 1]

            if tokens[token_index] == tokens[matched_prefix_length]:
                matched_prefix_length += 1
                prefix_lengths[token_index] = matched_prefix_length

        return prefix_lengths

    def _remaining_proposals_start_with_source(
        self,
        *,
        remaining_proposals: Sequence[Sequence[SourceToken]],
        expected_source_suffix: Sequence[str],
    ) -> bool:
        if not remaining_proposals or not expected_source_suffix:
            return False

        next_proposal_tokens = [token.text for token in remaining_proposals[0]]
        expected_prefix = list(expected_source_suffix[: len(next_proposal_tokens)])
        return next_proposal_tokens == expected_prefix

    def _reconstruct_spans(
        self,
        *,
        source_text: str,
        source_tokens: Sequence[SourceToken],
        token_ranges: Sequence[tuple[int, int]],
        section_title: str,
    ) -> list[SourceChunkSpan]:
        source_spans: list[SourceChunkSpan] = []

        for range_index, (token_start, token_end) in enumerate(token_ranges):
            span_start = 0 if range_index == 0 else source_tokens[token_start].start
            span_end = (
                source_tokens[token_end].start
                if token_end < len(source_tokens)
                else len(source_text)
            )
            span_text = source_text[span_start:span_end].strip()
            if not span_text:
                raise SourceChunkValidationError("invalid_span")

            source_spans.append(
                SourceChunkSpan(
                    text=span_text,
                    start=span_start,
                    end=span_end,
                    chunk_title=self.heading_resolver.resolve_title(
                        source_text=source_text,
                        span_start=span_start,
                        section_title=section_title,
                    ),
                )
            )

        return source_spans
