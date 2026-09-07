import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getBulaStatus, type UserBulaResponse } from "@/api/bulas";
import { UserBulaCard } from "@/components/bulas/user-bula-card";

vi.mock("@/api/bulas", async (importOriginal) => {
  const originalModule = await importOriginal<typeof import("@/api/bulas")>();
  return {
    ...originalModule,
    getBulaStatus: vi.fn(),
  };
});

const BULA_ID = "11111111-1111-4111-8111-111111111111";
const getBulaStatusMock = vi.mocked(getBulaStatus);

function buildUserBula(overrides: Partial<UserBulaResponse> = {}): UserBulaResponse {
  return {
    id: BULA_ID,
    user_id: 4,
    drug_name: "Dipirona",
    manufacturer: "Sanofi Medley",
    file_url: null,
    file_address: "stored_objects/dipirona",
    qdrant_collection: null,
    status: "processing",
    error_message: null,
    corpus: "private",
    created_at: "2026-09-07T12:00:00Z",
    updated_at: "2026-09-07T12:00:00Z",
    ...overrides,
  };
}

function renderUserBulaCard(bula: UserBulaResponse): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        gcTime: Number.POSITIVE_INFINITY,
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <UserBulaCard bula={bula} />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("UserBulaCard processing status", () => {
  it("polls every three seconds and stops after the bula becomes ready", async () => {
    vi.useFakeTimers();
    getBulaStatusMock
      .mockResolvedValueOnce({ id: BULA_ID, status: "processing", error_message: null })
      .mockResolvedValueOnce({ id: BULA_ID, status: "ready", error_message: null });
    renderUserBulaCard(buildUserBula());

    expect(screen.getByText("Processando...")).toBeInTheDocument();
    await act(async () => {
      await Promise.resolve();
    });
    expect(getBulaStatusMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_999);
    });
    expect(getBulaStatusMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(getBulaStatusMock).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Pronta")).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(9_000);
    });
    expect(getBulaStatusMock).toHaveBeenCalledTimes(2);
  });

  it("shows the terminal error and its safe message in a tooltip", async () => {
    const user = userEvent.setup();
    renderUserBulaCard(
      buildUserBula({
        status: "error",
        error_message: "Não foi possível extrair o texto do PDF.",
      })
    );

    expect(getBulaStatusMock).not.toHaveBeenCalled();
    const errorButton = screen.getByRole("button", {
      name: "Ver erro de processamento de Dipirona",
    });
    expect(screen.getByText("Erro")).toBeInTheDocument();

    await user.hover(errorButton);

    expect(await screen.findByRole("tooltip")).toHaveTextContent(
      "Não foi possível extrair o texto do PDF."
    );
  });
});
