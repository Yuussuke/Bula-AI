"""Shared source ranges for table-aware validation and deterministic splitting."""

from __future__ import annotations

from dataclasses import dataclass
import re


TABLE_SEPARATOR_PATTERN = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$"
)


@dataclass(frozen=True)
class SourceBlock:
    start: int
    end: int
    is_table: bool


def build_source_blocks(source: str) -> list[SourceBlock]:
    """Keep table captions and explicit footnotes attached to their grid."""
    paragraphs = list(re.finditer(r"\S[^\n]*(?:\n(?![ \t]*\n)[^\n]+)*", source))
    blocks: list[SourceBlock] = []
    for paragraph in paragraphs:
        value = paragraph.group()
        is_table = any(
            TABLE_SEPARATOR_PATTERN.match(line) for line in value.splitlines()
        )
        start = paragraph.start()
        if is_table and blocks and not blocks[-1].is_table:
            prefix = source[blocks[-1].start : blocks[-1].end].strip()
            if (
                "\n" not in prefix
                and len(prefix) <= 160
                and not prefix.endswith((".", "!", "?"))
            ):
                start = blocks.pop().start
        if (
            not is_table
            and blocks
            and blocks[-1].is_table
            and re.match(r"^\*{1,2}[^ *]", value)
        ):
            previous = blocks.pop()
            blocks.append(SourceBlock(previous.start, paragraph.end(), True))
        else:
            blocks.append(SourceBlock(start, paragraph.end(), is_table))
    return blocks
