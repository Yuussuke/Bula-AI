from app.modules.rag.base_chunker import BaseChunker, MarkdownSection


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

    def user_prompt(self, *, section: MarkdownSection) -> str:
        return (
            "Divida apenas o texto abaixo em chunks para RAG. "
            "Use somente trechos copiados do texto de origem; nao adicione, "
            "corrija ou complete nenhuma informacao medica. "
            "Se um trecho for curto, mantenha-o junto ao contexto mais proximo. "
            "Texto da secao:\n\n"
            f"{section.text}"
        )
