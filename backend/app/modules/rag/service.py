from __future__ import annotations

import asyncio
from uuid import UUID

from app.modules.bulas.models import Bula, BulaStatus
from app.modules.bulas.repository import BulaRepository
from app.modules.rag.base_chunker import BaseChunker
from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.parsers.pdf_parser import BulaParser
from app.modules.rag.qdrant_store import QdrantVectorStore, build_qdrant_point
from app.modules.rag.schemas import ChunkResult
from app.modules.storage.client import ObjectStoreClient


class BulaIngestionError(Exception):
    """Raised when a bula cannot be ingested into the dense vector store."""


class RAGIngestionService:
    def __init__(
        self,
        *,
        chunker: BaseChunker,
        parser: BulaParser,
        embeddings: EmbeddingAdapter,
        qdrant_store: QdrantVectorStore,
        object_store: ObjectStoreClient,
        bula_repo: BulaRepository,
    ) -> None:
        self.chunker = chunker
        self.parser = parser
        self.embeddings = embeddings
        self.qdrant_store = qdrant_store
        self.object_store = object_store
        self.bula_repo = bula_repo

    async def ingest_bula(self, *, bula_id: UUID) -> Bula:
        """
        Run the dense-only ingestion pipeline for one uploaded bula.

        This phase assumes the parser is text-based and OCR is disabled. Empty
        parse/chunk output is treated as an explicit document-quality failure.
        """
        bula = await self.bula_repo.get_by_id(bula_id=bula_id)
        if bula is None:
            raise BulaIngestionError("Bula not found.")

        if bula.status == BulaStatus.READY:
            return bula

        await self.bula_repo.update_ingestion_status(
            bula=bula,
            status=BulaStatus.PROCESSING,
            error_message=None,
        )

        if bula.file_address is None:
            raise BulaIngestionError("Bula does not have a stored PDF address.")

        stored_object_metadata = await self.object_store.get_metadata(bula.file_address)
        filename = stored_object_metadata.original_filename or f"{bula.id}.pdf"
        pdf_bytes = await self.object_store.get_bytes(bula.file_address)
        chunk_result = await self.parse_and_chunk_pdf(
            pdf_bytes=pdf_bytes,
            filename=filename,
            doc_id=str(bula.id),
        )

        if not chunk_result.chunks:
            raise BulaIngestionError("No chunks were generated from the PDF.")

        chunk_texts = [chunk.text for chunk in chunk_result.chunks]
        # LangChain exposes sync embed_documents here, so keep that provider call
        # off the event loop. Prefer a native async API if upstream adds one.
        vectors = await asyncio.to_thread(self.embeddings.embed_documents, chunk_texts)
        points = [
            build_qdrant_point(bula=bula, chunk=chunk, vector=vector)
            for chunk, vector in zip(chunk_result.chunks, vectors, strict=True)
        ]

        await self.qdrant_store.ensure_collection()
        await self.qdrant_store.upsert_points(points)

        return await self.bula_repo.update_ingestion_status(
            bula=bula,
            status=BulaStatus.READY,
            error_message=None,
            qdrant_collection=self.qdrant_store.collection_name,
        )

    async def chunk_markdown(self, *, markdown: str, doc_id: str) -> ChunkResult:
        return await self.chunker.chunk_markdown(markdown=markdown, doc_id=doc_id)

    async def parse_and_chunk_pdf(
        self,
        *,
        pdf_bytes: bytes,
        filename: str,
        doc_id: str,
    ) -> ChunkResult:
        parse_result = await self.parser.parse(pdf_bytes=pdf_bytes, filename=filename)
        if not parse_result.success:
            raise ValueError(parse_result.error or "PDF parsing failed.")

        return await self.chunk_markdown(markdown=parse_result.markdown, doc_id=doc_id)
