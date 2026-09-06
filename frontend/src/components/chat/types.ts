import type { SourceChunkResponse } from "@/api/chat";

export interface ChatTimelineMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sourceChunks: SourceChunkResponse[];
  deliveryStatus?: "sending" | "failed";
}

export interface ChatTimeline {
  sessionId: string;
  bulaId: string | null;
  messages: ChatTimelineMessage[];
}
