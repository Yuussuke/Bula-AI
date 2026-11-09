import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  type ChatSessionResponse,
  searchWorkspace,
  type WorkspaceSearchPage,
  type WorkspaceSearchResult,
} from "@/api/chat";
import { WorkspaceSearch } from "@/components/workspace-search";
import { useAuthStore } from "@/store/auth";

vi.mock("@/api/chat", () => ({ searchWorkspace: vi.fn() }));
const searchMock = vi.mocked(searchWorkspace);
const conversation: ChatSessionResponse = {
  id: "private-session",
  user_id: 1,
  bula_id: null,
  scope: "cross_bula",
  catalog_scope: "shared",
  title: "Cuidados com a losartana",
  created_at: "2026-11-08T12:00:00Z",
  updated_at: "2026-11-08T12:00:00Z",
  messages: [],
};
const chat: WorkspaceSearchResult = {
  kind: "chat",
  session: conversation,
  matched_in: "title",
  message_id: null,
  excerpt: null,
  matched_at: conversation.updated_at,
};

function LocationProbe(): ReactElement {
  const location = useLocation();
  return (
    <output data-testid="search-location">
      {location.pathname}
      {location.search}
    </output>
  );
}
function renderSearch(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <WorkspaceSearch />
        <button type="button">Outra ação</button>
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>
  );
}
beforeEach(() => {
  vi.resetAllMocks();
  useAuthStore.setState({
    user: { id: 1, name: "Allan Kita", email: "review@example.test", role: "user" },
  });
  searchMock.mockResolvedValue({ items: [chat], next_cursor: null });
});

describe("paged workspace search", () => {
  it("searches while typing and preserves the conversation's catalog", async () => {
    const user = userEvent.setup();
    renderSearch();
    expect(searchMock).not.toHaveBeenCalled();
    await user.type(screen.getByRole("searchbox"), "losartana");
    await user.click(await screen.findByRole("link", { name: /Cuidados com a losartana/ }));
    expect(screen.getByTestId("search-location")).toHaveTextContent(
      "/chat?catalogo=shared&session=private-session"
    );
    expect(searchMock).toHaveBeenCalledWith(
      { query: "losartana", kind: "all", cursor: undefined },
      expect.any(AbortSignal)
    );
    expect(
      screen.queryByRole("region", { name: "Resultados da pesquisa" })
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("loads the next page on scroll, keeps existing results, and shows loading placeholders", async () => {
    let finishPage!: (value: WorkspaceSearchPage) => void;
    const nextPage = new Promise<WorkspaceSearchPage>((resolve) => {
      finishPage = resolve;
    });
    searchMock
      .mockResolvedValueOnce({ items: [chat], next_cursor: "2:0" })
      .mockReturnValueOnce(nextPage);
    const user = userEvent.setup();
    renderSearch();
    await user.type(screen.getByRole("searchbox"), "los");
    const first = await screen.findByRole("link", { name: /Cuidados com a losartana/ });
    fireEvent.scroll(first.closest("ul")?.parentElement as HTMLElement);
    expect(await screen.findByRole("status", { name: "Carregando resultados" })).toBeVisible();
    expect(first).toBeVisible();
    await act(async () => {
      finishPage({
        items: [
          {
            ...chat,
            session: { ...conversation, id: "older", title: "Outra conversa" },
            matched_in: "message",
            message_id: "message-1",
            excerpt: "Estou testando a pesquisa",
          },
        ],
        next_cursor: null,
      });
      await nextPage;
    });
    const message = await screen.findByRole("link", { name: /Outra conversa/ });
    expect(message).toHaveAttribute(
      "href",
      "/chat?catalogo=shared&session=older&message=message-1"
    );
    expect(screen.getByText("Estou testando a pesquisa")).toBeVisible();
    expect(searchMock).toHaveBeenLastCalledWith(
      { query: "los", kind: "all", cursor: "2:0" },
      expect.any(AbortSignal)
    );
    expect(
      screen.queryByRole("button", { name: "Carregar mais resultados" })
    ).not.toBeInTheDocument();
  });

  it("resets pagination when changing the compact filter and keeps the query", async () => {
    const user = userEvent.setup();
    renderSearch();
    await user.type(screen.getByRole("searchbox"), "tes");
    await screen.findByRole("link", { name: /Cuidados com a losartana/ });
    await user.click(screen.getByRole("button", { name: "Medicamentos" }));
    await waitFor(() =>
      expect(searchMock).toHaveBeenLastCalledWith(
        { query: "tes", kind: "medications", cursor: undefined },
        expect.any(AbortSignal)
      )
    );
    expect(screen.getByRole("button", { name: "Medicamentos" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByRole("searchbox")).toHaveValue("tes");
    await user.click(screen.getByRole("button", { name: "Chats" }));
    await waitFor(() =>
      expect(searchMock).toHaveBeenLastCalledWith(
        { query: "tes", kind: "chats", cursor: undefined },
        expect.any(AbortSignal)
      )
    );
  });

  it("supports arrow navigation, Escape, and continued typing", async () => {
    const user = userEvent.setup();
    renderSearch();
    const field = screen.getByRole("searchbox");
    await user.type(field, "losartana");
    const result = await screen.findByRole("link", { name: /Cuidados com a losartana/ });
    await user.keyboard("{ArrowDown}");
    expect(result).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(field).toHaveFocus();
    expect(
      screen.queryByRole("region", { name: "Resultados da pesquisa" })
    ).not.toBeInTheDocument();
    await user.click(field);
    expect(await screen.findByRole("link", { name: /Cuidados com a losartana/ })).toBeVisible();
    await user.keyboard("{Escape}");
    await user.type(field, " ");
    expect(await screen.findByRole("link", { name: /Cuidados com a losartana/ })).toBeVisible();
  });

  it("closes outside and clears the field explicitly", async () => {
    const user = userEvent.setup();
    renderSearch();
    await user.type(screen.getByRole("searchbox"), "los");
    await screen.findByRole("link", { name: /Cuidados com a losartana/ });
    await user.click(screen.getByRole("button", { name: "Outra ação" }));
    expect(
      screen.queryByRole("region", { name: "Resultados da pesquisa" })
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("searchbox"));
    await user.click(screen.getByRole("button", { name: "Limpar pesquisa" }));
    expect(screen.getByRole("searchbox")).toHaveValue("");
    expect(screen.getByRole("searchbox")).toHaveFocus();
    expect(
      screen.queryByRole("region", { name: "Resultados da pesquisa" })
    ).not.toBeInTheDocument();
  });

  it("keeps earlier pages usable after a subsequent page fails and permits retry", async () => {
    searchMock
      .mockResolvedValueOnce({ items: [chat], next_cursor: "1:0" })
      .mockRejectedValueOnce(new Error("Unavailable"))
      .mockResolvedValueOnce({ items: [], next_cursor: null });
    const user = userEvent.setup();
    renderSearch();
    await user.type(screen.getByRole("searchbox"), "tes");
    await user.click(await screen.findByRole("button", { name: "Carregar mais resultados" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Não foi possível carregar mais resultados"
    );
    expect(screen.getByRole("link", { name: /Cuidados com a losartana/ })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
  });
});
