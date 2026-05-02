from app.modules.rag.base_chunker import BaseChunker
from app.modules.rag.parsers.pdf_parser import BulaParser
from app.modules.rag.schemas import ChunkResult


class RAGIngestionService:
    def __init__(self, *, chunker: BaseChunker, parser: BulaParser) -> None:
        self.chunker = chunker
        self.parser = parser

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
