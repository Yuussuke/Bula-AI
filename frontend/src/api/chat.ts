import { requestJson } from "@/lib/api";

const CHAT_SESSIONS_PREFIX = "/api/v1/chat/sessions";

export type RetrievalMode = "dense" | "bm25" | "hybrid";
export type ChatRole = "user" | "assistant";

export interface AskRequest {
  question: string;
  retrieval_mode?: RetrievalMode;
}

export interface SourceChunkResponse {
  section_title: string;
  chunk_text: string;
  relevance_score: number;
}

export interface AskResponse {
  session_id: string;
  answer: string;
  source_chunks: SourceChunkResponse[];
}

export interface ChatMessageResponse {
  id: string;
  session_id: string;
  role: ChatRole;
  content: string;
  retrieval_mode: RetrievalMode | null;
  source_chunks: SourceChunkResponse[];
  created_at: string;
  updated_at: string;
}

export interface ChatSessionResponse {
  id: string;
  user_id: number;
  bula_id: string | null;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessageResponse[];
}

export interface ListChatSessionsOptions {
  limit?: number;
  offset?: number;
}

export async function askBulaQuestion(bulaId: string, payload: AskRequest): Promise<AskResponse> {
  return requestJson<AskResponse>(`${CHAT_SESSIONS_PREFIX}/${bulaId}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildDenseAskPayload(payload)),
  });
}

export async function continueChatSession(
  sessionId: string,
  payload: AskRequest
): Promise<AskResponse> {
  return requestJson<AskResponse>(`${CHAT_SESSIONS_PREFIX}/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildDenseAskPayload(payload)),
  });
}

export async function getChatSession(sessionId: string): Promise<ChatSessionResponse> {
  return requestJson<ChatSessionResponse>(`${CHAT_SESSIONS_PREFIX}/${sessionId}`, {
    method: "GET",
  });
}

export async function listChatSessions({
  limit = 100,
  offset = 0,
}: ListChatSessionsOptions = {}): Promise<ChatSessionResponse[]> {
  const searchParams = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  return requestJson<ChatSessionResponse[]>(`${CHAT_SESSIONS_PREFIX}?${searchParams.toString()}`, {
    method: "GET",
  });
}

function buildDenseAskPayload(payload: AskRequest): Required<AskRequest> {
  return {
    question: payload.question,
    retrieval_mode: payload.retrieval_mode ?? "dense",
  };
}
