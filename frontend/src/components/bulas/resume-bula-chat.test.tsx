import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ChatSessionResponse, listChatSessions } from "@/api/chat";
import { ResumeBulaChat } from "@/components/bulas/resume-bula-chat";

vi.mock("@/api/chat", () => ({ listChatSessions: vi.fn() }));
const bulaId = "private-document";

function ChatDestination(): React.ReactElement {
  const location = useLocation();
  return <p>{location.search}</p>;
}
function renderResume(): void {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        <Routes>
          <Route path="/" element={<ResumeBulaChat bulaId={bulaId} />} />
          <Route path="/bulas/:bulaId/chat" element={<ChatDestination />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}
beforeEach(() => vi.clearAllMocks());

describe("resume private conversation", () => {
  it("loads only on demand and opens the most recently active scoped session", async () => {
    const session: ChatSessionResponse = {
      id: "recent-session",
      user_id: 1,
      bula_id: bulaId,
      scope: "bula",
      title: "Anterior",
      created_at: "2026-10-01T00:00:00Z",
      updated_at: "2026-10-02T00:00:00Z",
      messages: [],
    };
    vi.mocked(listChatSessions).mockResolvedValue([session]);
    renderResume();
    expect(listChatSessions).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole("button", { name: "Retomar última conversa" }));
    expect(await screen.findByText("?session=recent-session")).toBeInTheDocument();
    expect(listChatSessions).toHaveBeenCalledWith({
      scope: "bula",
      bulaId,
      sort: "updated_at",
      limit: 1,
    });
  });
  it("distinguishes no history from a failed request", async () => {
    vi.mocked(listChatSessions).mockResolvedValue([]);
    renderResume();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Retomar última conversa" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Nenhuma conversa anterior");
    vi.mocked(listChatSessions).mockRejectedValue(new Error("Unavailable"));
    await user.click(screen.getByRole("button", { name: "Retomar última conversa" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível buscar");
  });
});
