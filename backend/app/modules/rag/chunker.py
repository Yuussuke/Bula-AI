import json
from typing import Sequence

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

    def batch_user_prompt(self, *, sections: Sequence[MarkdownSection]) -> str:
        serialized_sections = [
            {
                "section_index": section.index,
                "section_title": section.title,
                "section_text": section.text,
            }
            for section in sections
        ]
        sections_json = json.dumps(serialized_sections, ensure_ascii=False)

        return (
            "Divida cada secao abaixo em chunks para RAG. "
            "Trate cada section_index de forma independente e nunca misture "
            "conteudo de secoes diferentes. Em cada chunk retornado, informe "
            "o section_index correspondente. Use somente trechos copiados da "
            "section_text de origem; nao adicione, corrija ou complete nenhuma "
            "informacao medica. Se um trecho for curto, mantenha-o junto apenas "
            "ao contexto da mesma secao. Secoes em JSON:\n\n"
            f"{sections_json}"
        )
