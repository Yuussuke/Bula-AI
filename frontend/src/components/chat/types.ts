import type { ChatScope, RetrievalMode, SourceChunkResponse } from "@/api/chat";
import type { CatalogScope } from "@/lib/catalog-scope";

export interface ChatTimelineMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sourceChunks: SourceChunkResponse[];
  retrievalMode?: RetrievalMode | null;
  deliveryStatus?: "sending" | "failed";
}

export interface ChatTimeline {
  catalogScope: CatalogScope;
  sessionId: string;
  bulaId: string | null;
  scope: ChatScope;
  hasInvalidMode: boolean;
  messages: ChatTimelineMessage[];
}
