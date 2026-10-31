import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { assignCurationRole, decideSharedBula, submitSharedBula } from "@/api/curation";
import { queryClient } from "@/lib/queryClient";
import { useAuthStore } from "@/store/auth";

const operationId = "11111111-1111-4111-8111-111111111111";
const account = {
  id: 7,
  name: "Synthetic user",
  email: "synthetic@example.com",
  role: "user" as const,
};

beforeEach(() => {
  useAuthStore
    .getState()
    .setAuth({ accessToken: "synthetic-token", user: { ...account, role: "admin" } });
});
afterEach(() => {
  vi.unstubAllGlobals();
  useAuthStore.getState().clearAuth();
  queryClient.clear();
});

describe("curation mutation transport", () => {
  it("keeps the explicit key on a multipart submission and sends its declared identity", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response("{}", { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["%PDF-1.7"], "original.pdf", { type: "application/pdf" });
    await submitSharedBula(
      {
        file,
        product_name: "Nome literal",
        manufacturer: null,
        source_url: "https://example.com/original.pdf",
        source_description: "Fonte identificada",
      },
      operationId
    );
    const request = fetchMock.mock.calls[0][1];
    expect(new Headers(request?.headers).get("Idempotency-Key")).toBe(operationId);
    expect(new Headers(request?.headers).get("Content-Type")).toBeNull();
    expect(request?.body).toBeInstanceOf(FormData);
    if (!(request?.body instanceof FormData)) throw new Error("Expected multipart upload");
    expect(request.body.get("product_name")).toBe("Nome literal");
    expect(request.body.get("source_url")).toBe("https://example.com/original.pdf");
  });

  it("preserves the same mutation key when authFetch refreshes an expired token", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(new Response("{}", { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: "synthetic-refreshed-token" }), { status: 200 })
      )
      .mockResolvedValueOnce(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const payload = {
      expected_version: 1,
      product_name: "Nome literal",
      reason: "Conferência documental",
    };
    await decideSharedBula("document-1", "approve", payload, operationId);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    const original = fetchMock.mock.calls[0][1];
    const retried = fetchMock.mock.calls[2][1];
    expect(new Headers(original?.headers).get("Idempotency-Key")).toBe(operationId);
    expect(new Headers(retried?.headers).get("Idempotency-Key")).toBe(operationId);
    expect(retried?.body).toBe(original?.body);
  });

  it("includes the role expectation and the same explicit operation key in an assignment", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await assignCurationRole(account, "reviewer", "Designação pelo responsável", operationId);
    const request = fetchMock.mock.calls[0][1];
    expect(new Headers(request?.headers).get("Idempotency-Key")).toBe(operationId);
    expect(request?.body).toBe(
      JSON.stringify({
        role: "reviewer",
        expected_role: "user",
        reason: "Designação pelo responsável",
      })
    );
  });
});
