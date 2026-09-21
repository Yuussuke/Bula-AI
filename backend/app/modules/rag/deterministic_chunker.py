from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal, Sequence

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.modules.rag.chunk_validation import SourceHeadingResolver
from app.modules.rag.token_estimator import TokenEstimator
from app.modules.rag.table_blocks import build_source_blocks


MarkdownBlockKind = Literal["list", "prose", "table"]

TABLE_SEPARATOR_PATTERN = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$"
)
LIST_ITEM_PATTERN = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")


@dataclass(frozen=True)
class MarkdownBlock:
    text: str
    start: int
    end: int
    kind: MarkdownBlockKind
    has_repeated_table_context: bool = False


@dataclass(frozen=True)
class DeterministicChunkDraft:
    text: str
    chunk_title: str
    has_repeated_table_context: bool = False


class DeterministicMarkdownSplitter:
    """Split Markdown locally while preserving source order and medical blocks."""

    def __init__(
        self,
        *,
        token_estimator: TokenEstimator,
        target_tokens: int,
        max_tokens: int,
        overlap_ratio: float,
        heading_resolver: SourceHeadingResolver | None = None,
    ) -> None:
        self.token_estimator = token_estimator
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.overlap_ratio = overlap_ratio
        self.heading_resolver = heading_resolver or SourceHeadingResolver()

    def split(
        self,
        *,
        source_text: str,
        section_title: str,
    ) -> list[DeterministicChunkDraft]:
        blocks = self._build_blocks(source_text)
        split_blocks = [
            split_block for block in blocks for split_block in self._split_block(block)
        ]
        packed_blocks = self._pack_blocks(split_blocks)

        return [
            DeterministicChunkDraft(
                text=block.text.strip(),
                chunk_title=self.heading_resolver.resolve_title(
                    source_text=source_text,
                    span_start=block.start,
                    section_title=section_title,
                ),
                has_repeated_table_context=block.has_repeated_table_context,
            )
            for block in packed_blocks
            if block.text.strip()
        ]

    def split_validated_text(
        self,
        *,
        source_text: str,
        section_title: str,
    ) -> list[DeterministicChunkDraft]:
        if self._estimate_tokens(source_text) <= self.max_tokens:
            return [
                DeterministicChunkDraft(
                    text=source_text.strip(),
                    chunk_title=self.heading_resolver.resolve_title(
                        source_text=source_text,
                        span_start=0,
                        section_title=section_title,
                    ),
                )
            ]

        return self.split(source_text=source_text, section_title=section_title)

    def _build_blocks(self, source_text: str) -> list[MarkdownBlock]:
        return [
            MarkdownBlock(
                text=source_text[block.start : block.end].strip(),
                start=block.start,
                end=block.end,
                kind="table"
                if block.is_table
                else self._classify_block(source_text[block.start : block.end]),
            )
            for block in build_source_blocks(source_text)
        ]

    def _classify_block(self, block_text: str) -> MarkdownBlockKind:
        lines = [line for line in block_text.splitlines() if line.strip()]
        if len(lines) >= 2 and any(
            TABLE_SEPARATOR_PATTERN.match(line) for line in lines
        ):
            return "table"

        if lines and LIST_ITEM_PATTERN.match(lines[0]):
            return "list"

        return "prose"

    def _split_block(self, block: MarkdownBlock) -> list[MarkdownBlock]:
        if self._estimate_tokens(block.text) <= self.max_tokens:
            return [block]

        if block.kind == "table":
            return self._split_table_block(block)

        if block.kind == "list":
            return self._split_list_block(block)

        return self._split_prose_block(block)

    def _split_table_block(self, block: MarkdownBlock) -> list[MarkdownBlock]:
        lines = block.text.splitlines()
        separator_index = next(
            (
                line_index
                for line_index, line in enumerate(lines)
                if TABLE_SEPARATOR_PATTERN.match(line)
            ),
            None,
        )
        if separator_index is None or separator_index == 0:
            return self._split_prose_block(block)

        header_lines = lines[: separator_index + 1]
        following_lines = lines[separator_index + 1 :]
        row_count = 0
        for line in following_lines:
            if not line.strip().startswith("|"):
                break
            row_count += 1
        data_rows = following_lines[:row_count]
        footnotes = following_lines[row_count:]
        if not data_rows:
            return self._split_prose_block(block)

        table_chunks: list[MarkdownBlock] = []
        current_rows: list[str] = []
        for data_row in data_rows:
            candidate_rows = [*current_rows, data_row]
            candidate_text = "\n".join([*header_lines, *candidate_rows, *footnotes])
            if current_rows and self._estimate_tokens(candidate_text) > self.max_tokens:
                table_chunks.extend(
                    self._build_bounded_block(
                        text="\n".join([*header_lines, *current_rows, *footnotes]),
                        source_block=block,
                        kind="table",
                    )
                )
                current_rows = [data_row]
                continue

            current_rows = candidate_rows

        if current_rows:
            table_chunks.extend(
                self._build_bounded_block(
                    text="\n".join([*header_lines, *current_rows, *footnotes]),
                    source_block=block,
                    kind="table",
                )
            )
        return table_chunks

    def _split_list_block(self, block: MarkdownBlock) -> list[MarkdownBlock]:
        items: list[list[str]] = []
        current_item: list[str] = []

        for line in block.text.splitlines():
            if LIST_ITEM_PATTERN.match(line):
                if current_item:
                    items.append(current_item)
                current_item = [line]
                continue

            current_item.append(line)

        if current_item:
            items.append(current_item)

        list_chunks: list[MarkdownBlock] = []
        current_items: list[str] = []
        for item_lines in items:
            item_text = "\n".join(item_lines)
            candidate_items = [*current_items, item_text]
            candidate_text = "\n".join(candidate_items)
            if (
                current_items
                and self._estimate_tokens(candidate_text) > self.max_tokens
            ):
                list_chunks.extend(
                    self._build_bounded_block(
                        text="\n".join(current_items),
                        source_block=block,
                        kind="list",
                    )
                )
                current_items = [item_text]
                continue

            current_items = candidate_items

        if current_items:
            list_chunks.extend(
                self._build_bounded_block(
                    text="\n".join(current_items),
                    source_block=block,
                    kind="list",
                )
            )
        return list_chunks

    def _build_bounded_block(
        self,
        *,
        text: str,
        source_block: MarkdownBlock,
        kind: MarkdownBlockKind,
    ) -> list[MarkdownBlock]:
        bounded_block = MarkdownBlock(
            text=text,
            start=source_block.start,
            end=source_block.end,
            kind=kind,
            has_repeated_table_context=kind == "table",
        )
        if self._estimate_tokens(text) <= self.max_tokens:
            return [bounded_block]
        if kind == "table":
            raise ValueError(
                "Table row and required context exceed the chunk token limit."
            )
        return self._split_prose_block(bounded_block)

    def _split_prose_block(self, block: MarkdownBlock) -> list[MarkdownBlock]:
        overlap_tokens = min(
            int(self.max_tokens * self.overlap_ratio),
            max(0, self.max_tokens - 1),
        )
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.max_tokens,
            chunk_overlap=overlap_tokens,
            length_function=self._estimate_tokens,
            separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
        )
        return [
            MarkdownBlock(
                text=chunk_text,
                start=block.start,
                end=block.end,
                kind=block.kind,
            )
            for chunk_text in splitter.split_text(block.text)
            if chunk_text.strip()
        ]

    def _pack_blocks(self, blocks: Sequence[MarkdownBlock]) -> list[MarkdownBlock]:
        packed_blocks: list[MarkdownBlock] = []
        current_blocks: list[MarkdownBlock] = []

        for block in blocks:
            candidate_text = "\n\n".join(
                [current_block.text for current_block in current_blocks] + [block.text]
            )
            should_flush = current_blocks and (
                self._estimate_tokens(candidate_text) > self.max_tokens
                or self._estimate_tokens(
                    "\n\n".join(current_block.text for current_block in current_blocks)
                )
                >= self.target_tokens
            )
            if should_flush:
                packed_blocks.append(self._merge_blocks(current_blocks))
                current_blocks = []

            current_blocks.append(block)

        if current_blocks:
            packed_blocks.append(self._merge_blocks(current_blocks))
        return packed_blocks

    def _merge_blocks(self, blocks: Sequence[MarkdownBlock]) -> MarkdownBlock:
        return MarkdownBlock(
            text="\n\n".join(block.text for block in blocks),
            start=blocks[0].start,
            end=blocks[-1].end,
            kind="prose",
            has_repeated_table_context=any(
                block.has_repeated_table_context for block in blocks
            ),
        )

    def _estimate_tokens(self, text: str) -> int:
        return self.token_estimator.estimate(text)
