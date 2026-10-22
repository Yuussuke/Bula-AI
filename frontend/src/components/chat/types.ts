import type { ChatScope, RetrievalMode, SourceChunkResponse } from "@/api/chat";

export interface ChatTimelineMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sourceChunks: SourceChunkResponse[];
  retrievalMode?: RetrievalMode | null;
  deliveryStatus?: "sending" | "failed";
}

export interface ChatTimeline {
  sessionId: string;
  bulaId: string | null;
  scope: ChatScope;
  messages: ChatTimelineMessage[];
}
