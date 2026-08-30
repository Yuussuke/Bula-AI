import json
from typing import Sequence

from app.modules.rag.base_chunker import BaseChunker, MarkdownSection
from app.modules.rag.semantic_chunking import (
    RETRIEVAL_V3_SYSTEM_PROMPT,
    RETRIEVAL_V3_USER_PROMPT_TEMPLATE,
)


class BulaChunker(BaseChunker):
    """Semantic chunker for Brazilian pharmaceutical leaflets (bulas)."""

    def system_prompt(self) -> str:
        return RETRIEVAL_V3_SYSTEM_PROMPT

    def user_prompt(self, *, section: MarkdownSection) -> str:
        return RETRIEVAL_V3_USER_PROMPT_TEMPLATE.format(
            section_text=section.text,
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
            "Divida cada fonte abaixo em chunks para busca semantica. "
            "Trate cada section_index de forma independente e nunca misture "
            "conteudo de secoes diferentes. Em cada chunk retornado, informe "
            "o section_index correspondente. Mantenha a ordem dos trechos e "
            "cubra cada section_text por completo. Use apenas texto copiado da "
            "fonte. Prefira limites entre paragrafos ou subtemas completos; "
            "preserve listas, composicao e dosagem intactas. Nunca resuma, "
            "corrija, reescreva, invente ou omita. Fontes em JSON:\n\n"
            f"{sections_json}"
        )
