import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  askBulaQuestion,
  type AskResponse,
  type ChatSessionResponse,
  continueChatSession,
  getChatSession,
  listChatSessions,
} from "@/api/chat";
import { ApiError } from "@/lib/api";
import { queryClient } from "@/lib/queryClient";
import { useAuthStore } from "@/store/auth";

const API_BASE_URL = "http://localhost:8000";
const BULA_ID = "11111111-1111-4111-8111-111111111111";
const SESSION_ID = "22222222-2222-4222-8222-222222222222";

function createJsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function expectAuthenticatedRequest(requestInit: RequestInit | undefined): void {
  expect(requestInit?.credentials).toBe("include");

  const requestHeaders = new Headers(requestInit?.headers);
  expect(requestHeaders.get("Authorization")).toBe("Bearer access-token");
}

describe("chat API", () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth({
      accessToken: "access-token",
      user: {
        id: 4,
        email: "user@bulaai.local",
        name: "Test User",
        role: "user",
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    useAuthStore.getState().clearAuth();
    queryClient.clear();
  });

  it("starts a session with dense retrieval by default", async () => {
    const askResponse: AskResponse = {
      session_id: SESSION_ID,
      answer: "Answer grounded in the leaflet.",
      source_chunks: [
        {
          section_title: "INDICATIONS",
          chunk_text: "Retrieved leaflet content.",
          relevance_score: 0.91,
        },
      ],
    };
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(createJsonResponse(askResponse));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      askBulaQuestion(BULA_ID, { question: "What is this medicine for?" })
    ).resolves.toEqual(askResponse);

    expect(fetchMock).toHaveBeenCalledOnce();
    const [requestUrl, requestInit] = fetchMock.mock.calls[0];
    expect(requestUrl).toBe(`${API_BASE_URL}/api/v1/chat/sessions/${BULA_ID}/ask`);
    expect(requestInit?.method).toBe("POST");
    expect(requestInit?.body).toBe(
      JSON.stringify({
        question: "What is this medicine for?",
        retrieval_mode: "dense",
      })
    );
    expectAuthenticatedRequest(requestInit);
  });

  it("continues and retrieves the same persisted session", async () => {
    const followUpResponse: AskResponse = {
      session_id: SESSION_ID,
      answer: "Follow-up answer grounded in the same leaflet.",
      source_chunks: [],
    };
    const sessionResponse: ChatSessionResponse = {
      id: SESSION_ID,
      user_id: 4,
      bula_id: BULA_ID,
      title: "What is this medicine for?",
      created_at: "2026-09-04T01:00:00Z",
      updated_at: "2026-09-04T01:01:00Z",
      messages: [
        {
          id: "44444444-4444-4444-8444-444444444444",
          session_id: SESSION_ID,
          role: "user",
          content: "And for children?",
          retrieval_mode: "dense",
          source_chunks: [],
          created_at: "2026-09-04T01:01:00Z",
          updated_at: "2026-09-04T01:01:00Z",
        },
      ],
    };
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock
      .mockResolvedValueOnce(createJsonResponse(followUpResponse))
      .mockResolvedValueOnce(createJsonResponse(sessionResponse));
    vi.stubGlobal("fetch", fetchMock);

    await continueChatSession(SESSION_ID, { question: "And for children?" });
    await expect(getChatSession(SESSION_ID)).resolves.toEqual(sessionResponse);

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      `${API_BASE_URL}/api/v1/chat/sessions/${SESSION_ID}/messages`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          question: "And for children?",
          retrieval_mode: "dense",
        }),
      })
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `${API_BASE_URL}/api/v1/chat/sessions/${SESSION_ID}`,
      expect.objectContaining({ method: "GET" })
    );
  });

  it("lists the authenticated user's recent sessions", async () => {
    const sessions = [
      {
        id: SESSION_ID,
        user_id: 4,
        bula_id: BULA_ID,
        title: "What is this medicine for?",
        created_at: "2026-09-04T01:00:00Z",
        updated_at: "2026-09-04T01:01:00Z",
        messages: [],
      },
    ];
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(createJsonResponse(sessions));
    vi.stubGlobal("fetch", fetchMock);

    await expect(listChatSessions({ limit: 20, offset: 0 })).resolves.toEqual(sessions);

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/chat/sessions?limit=20&offset=0`,
      expect.objectContaining({ method: "GET" })
    );
    expectAuthenticatedRequest(fetchMock.mock.calls[0][1]);
  });

  it("exposes the response status and safe API message on failure", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(createJsonResponse({ detail: "Chat session not found." }, 404));
    vi.stubGlobal("fetch", fetchMock);

    const request = getChatSession(SESSION_ID);

    await expect(request).rejects.toBeInstanceOf(ApiError);
    await expect(request).rejects.toMatchObject({
      status: 404,
      message: "Chat session not found.",
    });
  });
});
