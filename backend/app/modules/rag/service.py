from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from app.modules.bulas.models import (
    Bula,
    BulaCorpus,
    BulaStatus,
    SystemBulaPublicationState,
)
from app.modules.bulas.repository import BulaRepository
from app.modules.rag.base_chunker import BaseChunker
from app.modules.rag.debug_artifacts import (
    DebugArtifactStatus,
    RAGIngestionDebugArtifacts,
)
from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.observability import RAGIngestionObserver
from app.modules.rag.parsers.pdf_parser import BulaParser, ParseResult
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
        debug_artifacts: RAGIngestionDebugArtifacts | None = None,
    ) -> None:
        self.chunker = chunker
        self.parser = parser
        self.embeddings = embeddings
        self.qdrant_store = qdrant_store
        self.object_store = object_store
        self.bula_repo = bula_repo
        self.debug_artifacts = debug_artifacts or RAGIngestionDebugArtifacts(
            enabled=False,
            root_path="tmp/rag-ingestion-debug",
        )

    async def ingest_bula(self, *, bula_id: UUID) -> Bula:
        """
        Run the dense-only ingestion pipeline for one uploaded bula.

        This phase assumes the parser is text-based and OCR is disabled. Empty
        parse/chunk output is treated as an explicit document-quality failure.
        """
        run_id = str(uuid4())
        doc_id = str(bula_id)
        observer = RAGIngestionObserver(
            run_id=run_id,
            bula_id=doc_id,
            doc_id=doc_id,
        )
        observer.start()
        ingestion_error: BaseException | None = None

        try:
            async with observer.stage("bula_lookup") as stage:
                bula = await self.bula_repo.get_by_id(bula_id=bula_id)
                if bula is None:
                    raise BulaIngestionError("Bula not found.")

                stage.add_fields(
                    current_status=bula.status.value,
                    is_already_ready=bula.status == BulaStatus.READY,
                )

            assert bula is not None
            if bula.status == BulaStatus.READY:
                return bula

            publication = bula.system_publication
            if (
                bula.corpus == BulaCorpus.SYSTEM
                and publication is not None
                and publication.state != SystemBulaPublicationState.STAGED
            ):
                async with observer.stage("reset_publication"):
                    await self.bula_repo.reset_system_publication_for_reingestion(
                        publication=publication,
                    )

            async with observer.stage("mark_processing") as stage:
                bula = await self.bula_repo.update_ingestion_status(
                    bula=bula,
                    status=BulaStatus.PROCESSING,
                    error_message=None,
                )
                stage.add_fields(target_status=BulaStatus.PROCESSING.value)

            filename = f"{bula.id}.pdf"
            file_address = ""
            async with observer.stage("object_metadata") as stage:
                file_address = bula.file_address or ""
                if not file_address:
                    raise BulaIngestionError("Bula does not have a stored PDF address.")

                stored_object_metadata = await self.object_store.get_metadata(
                    file_address
                )
                filename = stored_object_metadata.original_filename or filename
                stage.add_fields(
                    pdf_size_bytes=stored_object_metadata.content_size_bytes,
                )

            async with observer.stage("pdf_download") as stage:
                pdf_bytes = await self.object_store.get_bytes(file_address)
                stage.add_fields(pdf_size_bytes=len(pdf_bytes))

            parse_result: ParseResult | None = None
            try:
                async with observer.stage("pdf_parse_to_markdown") as stage:
                    parse_result = await self.parser.parse(
                        pdf_bytes=pdf_bytes,
                        filename=filename,
                    )
                    stage.add_fields(
                        extraction_tier=parse_result.extraction_tier,
                        section_count=len(parse_result.sections),
                    )

                    if not parse_result.success:
                        raise ValueError(parse_result.error or "PDF parsing failed.")
            except Exception as exc:
                if parse_result is not None and not parse_result.success:
                    async with observer.stage("write_debug_artifacts"):
                        await self._write_debug_artifacts(
                            run_id=run_id,
                            doc_id=doc_id,
                            filename=filename,
                            status="parse_failed",
                            parse_result=parse_result,
                            error=exc,
                        )
                raise

            chunk_result: ChunkResult | None = None
            try:
                async with observer.stage("chunk_markdown") as stage:
                    chunk_result = await self.chunk_markdown(
                        markdown=parse_result.markdown,
                        doc_id=doc_id,
                    )
                    stage.add_fields(
                        section_count=chunk_result.metadata.get(
                            "section_count",
                            len(parse_result.sections),
                        ),
                        batch_count=chunk_result.metadata.get("batch_count"),
                        model_call_count=chunk_result.metadata.get("model_call_count"),
                        batch_fallback_count=chunk_result.metadata.get(
                            "batch_fallback_count"
                        ),
                        chunk_validation=chunk_result.metadata.get("validation"),
                        chunk_fallback=chunk_result.metadata.get("fallback"),
                        semantic_chunking=chunk_result.metadata.get(
                            "semantic_chunking"
                        ),
                        chunk_count=len(chunk_result.chunks),
                    )

                    if not chunk_result.chunks:
                        raise BulaIngestionError(
                            "No chunks were generated from the PDF."
                        )
            except Exception as exc:
                async with observer.stage("write_debug_artifacts"):
                    await self._write_debug_artifacts(
                        run_id=run_id,
                        doc_id=doc_id,
                        filename=filename,
                        status="chunking_failed",
                        parse_result=parse_result,
                        markdown=parse_result.markdown,
                        chunk_result=chunk_result,
                        error=exc,
                    )
                raise

            async with observer.stage("write_debug_artifacts"):
                await self._write_debug_artifacts(
                    run_id=run_id,
                    doc_id=doc_id,
                    filename=filename,
                    status="success",
                    parse_result=parse_result,
                    markdown=parse_result.markdown,
                    chunk_result=chunk_result,
                )

            chunk_texts = [chunk.text for chunk in chunk_result.chunks]
            async with observer.stage("embed_chunks") as stage:
                stage.add_fields(chunk_count=len(chunk_texts))
                # LangChain exposes sync embed_documents here, so keep that provider
                # call off the event loop. Prefer a native async API if upstream adds one.
                vectors = await asyncio.to_thread(
                    self.embeddings.embed_documents,
                    chunk_texts,
                )
                stage.add_fields(embedding_vector_count=len(vectors))

            points = [
                build_qdrant_point(
                    bula=bula,
                    chunk=chunk,
                    vector=vector,
                    embedding_profile=self.embeddings.embedding_profile,
                )
                for chunk, vector in zip(chunk_result.chunks, vectors, strict=True)
            ]

            async with observer.stage("qdrant_ensure_collection") as stage:
                await self.qdrant_store.ensure_collection()
                stage.add_fields(qdrant_collection=self.qdrant_store.collection_name)

            async with observer.stage("qdrant_upsert") as stage:
                qdrant_point_count = await self.qdrant_store.upsert_points(points)
                stage.add_fields(
                    qdrant_collection=self.qdrant_store.collection_name,
                    qdrant_point_count=qdrant_point_count,
                )

            async with observer.stage("mark_ready") as stage:
                ready_bula = await self.bula_repo.update_ingestion_status(
                    bula=bula,
                    status=BulaStatus.READY,
                    error_message=None,
                    qdrant_collection=self.qdrant_store.collection_name,
                )
                stage.add_fields(
                    target_status=BulaStatus.READY.value,
                    qdrant_collection=self.qdrant_store.collection_name,
                )
                return ready_bula
        except BaseException as exc:
            ingestion_error = exc
            raise
        finally:
            observer.finish(error=ingestion_error)

    async def chunk_markdown(self, *, markdown: str, doc_id: str) -> ChunkResult:
        return await self.chunker.chunk_markdown(markdown=markdown, doc_id=doc_id)

    async def _write_debug_artifacts(
        self,
        *,
        run_id: str,
        doc_id: str,
        filename: str,
        status: DebugArtifactStatus,
        parse_result: ParseResult | None,
        markdown: str | None = None,
        chunk_result: ChunkResult | None = None,
        error: BaseException | None = None,
    ) -> None:
        await self.debug_artifacts.write_run_artifacts(
            run_id=run_id,
            doc_id=doc_id,
            filename=filename,
            status=status,
            parse_result=parse_result,
            markdown=markdown,
            chunk_result=chunk_result,
            chunking_config=self.chunker.config,
            error=error,
        )

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
