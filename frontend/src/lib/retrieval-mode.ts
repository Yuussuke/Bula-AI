import type { RetrievalMode } from "@/api/chat";

export const RETRIEVAL_MODES: Record<RetrievalMode, { label: string; description: string }> = {
  dense: {
    label: "Semântico",
    description: "Busca por significado e por formas diferentes de expressar a dúvida.",
  },
  bm25: { label: "Palavras-chave", description: "Busca por termos presentes nos documentos." },
  hybrid: {
    label: "Híbrido",
    description: "Combina as buscas semântica e por palavras-chave. É o padrão do assistente.",
  },
};

export function isRetrievalMode(value: unknown): value is RetrievalMode {
  return typeof value === "string" && Object.hasOwn(RETRIEVAL_MODES, value);
}
