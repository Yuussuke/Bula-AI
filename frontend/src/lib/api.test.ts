import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { authFetch, SessionExpiredError } from "@/lib/api";
import { queryClient } from "@/lib/queryClient";
import { useAuthStore } from "@/store/auth";

const API_BASE_URL = "http://localhost:8000";
const REFRESH_URL = `${API_BASE_URL}/api/v1/auth/refresh`;

function createJsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function getRequestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") {
    return input;
  }

  if (input instanceof URL) {
    return input.toString();
  }

  return input.url;
}

function getAuthorizationHeader(requestInit: RequestInit | undefined): string | null {
  return new Headers(requestInit?.headers).get("Authorization");
}

describe("authFetch", () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth({
      accessToken: "expired-access-token",
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

  it("shares one refresh while retrying concurrent protected requests", async () => {
    const firstPath = "/api/v1/chat/sessions/first";
    const secondPath = "/api/v1/chat/sessions/second";
    const fetchMock = vi.fn<typeof fetch>();

    fetchMock.mockImplementation((input, requestInit) => {
      const requestUrl = getRequestUrl(input);
      if (requestUrl === REFRESH_URL) {
        return Promise.resolve(
          createJsonResponse({ access_token: "new-access-token", token_type: "bearer" })
        );
      }

      const authorizationHeader = getAuthorizationHeader(requestInit);
      if (authorizationHeader === "Bearer expired-access-token") {
        return Promise.resolve(new Response(null, { status: 401 }));
      }

      return Promise.resolve(createJsonResponse({ requestUrl }));
    });
    vi.stubGlobal("fetch", fetchMock);

    const [firstResponse, secondResponse] = await Promise.all([
      authFetch(firstPath),
      authFetch(secondPath),
    ]);

    expect(firstResponse.ok).toBe(true);
    expect(secondResponse.ok).toBe(true);

    const refreshCalls = fetchMock.mock.calls.filter(
      ([input]) => getRequestUrl(input) === REFRESH_URL
    );
    expect(refreshCalls).toHaveLength(1);

    for (const path of [firstPath, secondPath]) {
      const protectedCalls = fetchMock.mock.calls.filter(
        ([input]) => getRequestUrl(input) === `${API_BASE_URL}${path}`
      );

      expect(protectedCalls).toHaveLength(2);
      expect(getAuthorizationHeader(protectedCalls[0]?.[1])).toBe("Bearer expired-access-token");
      expect(getAuthorizationHeader(protectedCalls[1]?.[1])).toBe("Bearer new-access-token");
    }

    expect(useAuthStore.getState().accessToken).toBe("new-access-token");
  });

  it("clears authentication and private cache when refresh fails", async () => {
    queryClient.setQueryData(["private-session"], { id: "private" });

    const fetchMock = vi.fn<typeof fetch>();
    fetchMock
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(null, { status: 401 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(authFetch("/api/v1/chat/sessions/private")).rejects.toBeInstanceOf(
      SessionExpiredError
    );

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(getRequestUrl(fetchMock.mock.calls[1]?.[0])).toBe(REFRESH_URL);
    expect(useAuthStore.getState()).toMatchObject({
      accessToken: null,
      user: null,
      isAuthenticated: false,
    });
    expect(queryClient.getQueryData(["private-session"])).toBeUndefined();
  });
});
