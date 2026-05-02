from app.modules.rag.base_chunker import BaseChunker


class BulaChunker(BaseChunker):
    """Semantic chunker for Brazilian pharmaceutical leaflets (bulas)."""

    def system_prompt(self) -> str:
        return (
            "Voce e um especialista em chunking semantico para RAG em portugues "
            "brasileiro. Divida o texto em chunks semanticamente coesos, sem "
            "cortar frases no meio. Preserve listas medicas, blocos de posologia "
            "e contraindicacao intactos. "
            f"Meta: ~{self.config.target_tokens} tokens por chunk "
            f"(min {self.config.min_tokens}, max {self.config.max_tokens}). "
            "Retorne SOMENTE JSON valido seguindo o schema fornecido."
        )
