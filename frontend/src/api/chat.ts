import { requestJson } from "@/lib/api";

const CHAT_SESSIONS_PREFIX = "/api/v1/chat/sessions";

export type RetrievalMode = "dense" | "bm25" | "hybrid";
export type ChatRole = "user" | "assistant";
export type ChatScope = "bula" | "cross_bula";
export type ChatContext = { scope: "bula"; bulaId: string } | { scope: "cross_bula" };

export interface AskRequest {
  question: string;
  mode?: RetrievalMode;
}

export interface SourceChunkResponse {
  chunk_id?: string | null;
  bula_id?: string | null;
  drug_name?: string | null;
  manufacturer?: string | null;
  presentation?: string | null;
  strength?: string | null;
  source_url?: string | null;
  section_title: string;
  chunk_text: string;
  relevance_score: number;
}

export interface SourceBulaResponse {
  bula_id: string;
  drug_name: string;
  manufacturer?: string | null;
  presentation?: string | null;
  strength?: string | null;
  source_url?: string | null;
}

export interface AskResponse {
  session_id: string;
  answer: string;
  retrieval_mode: RetrievalMode;
  source_chunks: SourceChunkResponse[];
  source_bulas?: SourceBulaResponse[];
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
  scope?: ChatScope;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessageResponse[];
}

export interface ListChatSessionsOptions {
  limit?: number;
  offset?: number;
  scope?: ChatScope;
  bulaId?: string;
  sort?: "created_at" | "updated_at";
}

export async function askCrossBulaQuestion(payload: AskRequest): Promise<AskResponse> {
  return requestJson<AskResponse>("/api/v1/chat/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function askBulaQuestion(bulaId: string, payload: AskRequest): Promise<AskResponse> {
  return requestJson<AskResponse>(`${CHAT_SESSIONS_PREFIX}/${bulaId}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function continueChatSession(
  sessionId: string,
  payload: AskRequest
): Promise<AskResponse> {
  return requestJson<AskResponse>(`${CHAT_SESSIONS_PREFIX}/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
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
  scope,
  bulaId,
  sort,
}: ListChatSessionsOptions = {}): Promise<ChatSessionResponse[]> {
  const searchParams = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (scope) searchParams.set("scope", scope);
  if (bulaId) searchParams.set("bula_id", bulaId);
  if (sort) searchParams.set("sort", sort);

  return requestJson<ChatSessionResponse[]>(`${CHAT_SESSIONS_PREFIX}?${searchParams.toString()}`, {
    method: "GET",
  });
}
