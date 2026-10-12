"""Deterministic lexical discovery, never automatic semantic approval."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
import re
import unicodedata

from evaluation.artifacts import digest_value
from evaluation.contracts import (
    MappingInput,
    MappingOutput,
    MappingStatus,
    ReferenceMatch,
    SnapshotChunk,
)


@dataclass(frozen=True)
class CandidatePolicy:
    version: str = "lexical_discovery_v1"
    minimum_partial_tokens: int = 5
    minimum_partial_coverage: float = 0.35
    maximum_adjacent_chunks: int = 3


def tokens(text: str) -> tuple[str, ...]:
    """Formatting-only comparison. No unit, decimal or medical normalization."""
    value = unicodedata.normalize("NFKC", text).casefold().replace("\u00ad", "")
    value = re.sub(r"<br\s*/?>", " ", value)
    return tuple(re.findall(r"\d+(?:[.,]\d+)*|[^\W\d_]+|[%°/+<>=−-]", value))


@dataclass(frozen=True)
class Candidate:
    chunk_ids: tuple[str, ...]
    method: str
    matched_reference_token_positions: tuple[int, ...]
    token_coverage: float
    section_agreement: bool
    source_role: str
    rationale: str


class EvidenceCandidateMapper:
    def __init__(self, policy: CandidatePolicy = CandidatePolicy()) -> None:
        self.policy = policy

    def match_token_sequences(
        self, reference_tokens: tuple[str, ...], chunk_tokens: tuple[str, ...]
    ) -> tuple[bool, tuple[int, ...], int]:
        if not reference_tokens:
            raise ValueError("Empty documentary quote")
        matcher = SequenceMatcher(None, reference_tokens, chunk_tokens, autojunk=False)
        blocks = matcher.get_matching_blocks()
        positions = tuple(
            sorted(
                {
                    index
                    for block in blocks
                    for index in range(block.a, block.a + block.size)
                }
            )
        )
        longest = max(block.size for block in blocks)
        return longest == len(reference_tokens), positions, longest

    def discover(
        self, mapping_input: MappingInput
    ) -> tuple[MappingOutput, dict[str, tuple[Candidate, ...]]]:
        mapping_input.validate()
        candidates_by_reference: dict[str, tuple[Candidate, ...]] = {}
        matches = []
        chunk_tokens = [tokens(chunk.text) for chunk in mapping_input.chunks]
        for reference in mapping_input.references:
            reference_tokens = tokens(reference.quote)
            candidates = []
            full_sets: set[tuple[str, ...]] = set()
            for index, chunk in enumerate(mapping_input.chunks):
                full, positions, longest = self.match_token_sequences(
                    reference_tokens, chunk_tokens[index]
                )
                coverage = len(positions) / len(reference_tokens)
                if not full and (
                    longest < self.policy.minimum_partial_tokens
                    or coverage < self.policy.minimum_partial_coverage
                ):
                    continue
                metadata = chunk.text.lstrip().startswith("---")
                if full and not metadata:
                    full_sets.add((chunk.chunk_id,))
                candidates.append(
                    Candidate(
                        (chunk.chunk_id,),
                        "literal_token_sequence" if full else "partial_token_sequences",
                        positions,
                        round(coverage, 6),
                        self._section_agrees(reference.section, chunk),
                        "metadata_requires_source_confirmation"
                        if metadata
                        else "source_text",
                        "Ordered literal tokens match; PDF context and semantic sufficiency remain unconfirmed."
                        if full
                        else "Partial ordered text only; matching words do not establish documentary support.",
                    )
                )
            # Ordered windows are source chunk adjacency, not retrieved ranks.
            for width in range(2, self.policy.maximum_adjacent_chunks + 1):
                for start in range(len(mapping_input.chunks) - width + 1):
                    group = mapping_input.chunks[start : start + width]
                    if any(chunk.text.lstrip().startswith("---") for chunk in group):
                        continue
                    identifiers = tuple(chunk.chunk_id for chunk in group)
                    if any(set(existing) <= set(identifiers) for existing in full_sets):
                        continue
                    combined = tuple(
                        token
                        for part in chunk_tokens[start : start + width]
                        for token in part
                    )
                    full, positions, _ = self.match_token_sequences(
                        reference_tokens, combined
                    )
                    if full:
                        full_sets.add(identifiers)
                        candidates.append(
                            Candidate(
                                identifiers,
                                "adjacent_literal_token_sequence",
                                positions,
                                1.0,
                                any(
                                    self._section_agrees(reference.section, chunk)
                                    for chunk in group
                                ),
                                "source_text",
                                "Quote occurs across consecutive indexed chunks; inspect overlap, scope and structural context.",
                            )
                        )
            identifiers = tuple(
                dict.fromkeys(
                    identifier
                    for candidate in candidates
                    for identifier in candidate.chunk_ids
                )
            )
            status: MappingStatus
            if not candidates:
                status = "absent"
            elif len(full_sets) > 1:
                status = "ambiguous"
            elif full_sets:
                status = "complete"
            else:
                status = "partial"
            matches.append(
                ReferenceMatch(
                    reference.reference_id,
                    identifiers,
                    status,
                    "Lexical discovery status only; no human semantic approval or retrieval ranking.",
                )
            )
            candidates_by_reference[reference.reference_id] = tuple(candidates)
        statuses = {match.status for match in matches}
        overall: MappingStatus
        if statuses == {"complete"}:
            overall = "complete"
        elif "ambiguous" in statuses:
            overall = "ambiguous"
        elif statuses == {"absent"}:
            overall = "absent"
        else:
            overall = "partial"
        output = MappingOutput(
            digest_value(asdict(mapping_input)), overall, tuple(matches)
        )
        output.validate(mapping_input)
        return output, candidates_by_reference

    def _section_agrees(self, section: str, chunk: SnapshotChunk) -> bool:
        expected, actual = set(tokens(section)), set(tokens(chunk.section))
        return bool(
            expected
            and actual
            and min(len(expected), len(actual)) >= 2
            and len(expected & actual) / len(expected | actual) >= 0.7
        )
