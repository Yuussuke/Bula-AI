"""Export a local PDF parsing and deterministic chunking preview.

This command never writes to PostgreSQL or Qdrant and never calls a model.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import cast

from openai import AsyncOpenAI

from app.modules.rag.chunker import BulaChunker
from app.modules.rag.debug_artifacts import RAGIngestionDebugArtifacts
from app.modules.rag.parsers.pdf_parser import BulaParser
from app.modules.rag.schemas import ChunkingConfig
from app.modules.rag.token_estimator import TiktokenTokenEstimator


class UnusedModelClient:
    """Placeholder: semantic chunking is disabled for this preview."""


async def export_preview(*, pdf_path: Path, output_path: Path) -> None:
    pdf_bytes = pdf_path.read_bytes()
    parse_result = await BulaParser(ocr_enabled=False).parse(
        pdf_bytes=pdf_bytes,
        filename=pdf_path.name,
    )
    if not parse_result.success:
        raise RuntimeError(parse_result.error or "PDF parsing failed")

    chunking_config = ChunkingConfig(is_llm_enabled=False)
    chunker = BulaChunker(
        llm=cast(AsyncOpenAI, UnusedModelClient()),
        config=chunking_config,
        token_estimator=TiktokenTokenEstimator(encoding_name="cl100k_base"),
    )
    chunk_result = await chunker.chunk_markdown(
        markdown=parse_result.markdown,
        doc_id=pdf_path.stem,
    )
    debug_writer = RAGIngestionDebugArtifacts(
        enabled=True,
        root_path=output_path,
    )
    write_result = await debug_writer.write_run_artifacts(
        run_id="deterministic-preview",
        doc_id=pdf_path.stem,
        filename=pdf_path.name,
        status="success",
        parse_result=parse_result,
        markdown=parse_result.markdown,
        chunk_result=chunk_result,
        chunking_config=chunking_config,
    )
    if write_result.artifact_write_failures:
        raise RuntimeError(
            f"Could not write preview: {write_result.artifact_write_failures}"
        )

    print(f"Preview: {output_path / pdf_path.stem / 'deterministic-preview'}")
    print(f"Parser: {parse_result.parser_version}")
    print(f"Chunks: {len(chunk_result.chunks)} (deterministic fallback)")


def main() -> None:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("pdf_path", type=Path)
    argument_parser.add_argument(
        "--output",
        type=Path,
        default=Path("tmp/rag-ingestion-debug/manual-preview"),
    )
    arguments = argument_parser.parse_args()
    asyncio.run(
        export_preview(pdf_path=arguments.pdf_path, output_path=arguments.output)
    )


if __name__ == "__main__":
    main()
