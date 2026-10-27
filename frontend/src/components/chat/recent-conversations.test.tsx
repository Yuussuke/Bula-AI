import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ChatSessionResponse, listChatSessions } from "@/api/chat";
import { RecentConversations } from "@/components/chat/recent-conversations";

vi.mock("@/api/chat", () => ({ listChatSessions: vi.fn() }));
const listSessionsMock = vi.mocked(listChatSessions);

function session(
  id: string,
  scope: "bula" | "cross_bula",
  bulaId: string | null = null
): ChatSessionResponse {
  return {
    id,
    scope,
    bula_id: bulaId,
    user_id: 1,
    title: `Conversa ${id}`,
    created_at: "2026-10-25T10:00:00Z",
    updated_at: "2026-10-26T12:00:00Z",
    messages: [],
  };
}

function renderNavigation(props: ComponentProps<typeof RecentConversations> = {}): QueryClient {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <RecentConversations {...props} />
      </MemoryRouter>
    </QueryClientProvider>
  );
  return queryClient;
}

beforeEach(() => {
  vi.clearAllMocks();
  listSessionsMock.mockImplementation(({ scope } = {}) =>
    Promise.resolve(
      scope === "cross_bula"
        ? [session("geral", "cross_bula")]
        : [session("losartana", "bula", "pdf-losartana")]
    )
  );
});

describe("recent conversations", () => {
  it("shows both scopes and reopens each with its own document and session", async () => {
    renderNavigation({ context: { scope: "cross_bula" } });
    expect(await screen.findByRole("link", { name: /Conversa losartana/ })).toHaveAttribute(
      "href",
      "/bulas/pdf-losartana/chat?session=losartana"
    );
    expect(screen.getByRole("link", { name: /Conversa geral/ })).toHaveAttribute(
      "href",
      "/chat?session=geral"
    );
    expect(listSessionsMock).toHaveBeenCalledWith({
      scope: "bula",
      limit: 10,
      offset: 0,
      sort: "updated_at",
    });
    expect(listSessionsMock).toHaveBeenCalledWith({
      scope: "cross_bula",
      limit: 10,
      offset: 0,
      sort: "updated_at",
    });
  });

  it("opens and closes each group independently using the keyboard", async () => {
    const user = userEvent.setup();
    renderNavigation();
    await screen.findByText("Conversa losartana");
    const generalTrigger = screen.getByRole("button", { name: "Chat geral" });
    await user.click(generalTrigger);
    expect(generalTrigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("link", { name: /Conversa geral/ })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Conversa losartana/ })).toBeVisible();
    await user.keyboard("{Enter}");
    expect(generalTrigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("link", { name: /Conversa geral/ })).toBeVisible();
  });

  it("starts a new turn in the current context and offers the other scope separately", async () => {
    const user = userEvent.setup();
    const startNewSession = vi.fn();
    const navigate = vi.fn();
    renderNavigation({
      context: { scope: "bula", bulaId: "pdf-losartana" },
      onStartNewSession: startNewSession,
      onNavigate: navigate,
      currentSessionId: "losartana",
    });
    await screen.findByText("Conversa losartana");
    expect(screen.getByRole("link", { name: /Conversa losartana/ })).toHaveAttribute(
      "aria-current",
      "page"
    );
    await user.click(screen.getByRole("button", { name: "Nova conversa desta bula" }));
    expect(startNewSession).toHaveBeenCalledOnce();
    expect(navigate).toHaveBeenCalledOnce();
    expect(screen.getByRole("link", { name: "Nova conversa geral" })).toHaveAttribute(
      "href",
      "/chat"
    );
  });

  it("paginates medication conversations without changing the general list", async () => {
    const firstPage = Array.from({ length: 10 }, (_, index) =>
      session(`bula-${index}`, "bula", `pdf-${index}`)
    );
    listSessionsMock.mockImplementation(({ scope, offset } = {}) => {
      if (scope === "cross_bula") return Promise.resolve([session("geral", "cross_bula")]);
      return Promise.resolve(offset === 0 ? firstPage : [session("antiga", "bula", "pdf-antigo")]);
    });
    const user = userEvent.setup();
    renderNavigation();
    await user.click(await screen.findByRole("button", { name: "Mostrar mais conversas" }));
    expect(await screen.findByRole("link", { name: /Conversa antiga/ })).toHaveAttribute(
      "href",
      "/bulas/pdf-antigo/chat?session=antiga"
    );
    expect(listSessionsMock).toHaveBeenCalledWith({
      scope: "bula",
      sort: "updated_at",
      limit: 10,
      offset: 10,
    });
    expect(screen.getByRole("link", { name: /Conversa geral/ })).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "Mostrar mais conversas" })
    ).not.toBeInTheDocument();
  });

  it("does not turn orphaned or incorrectly scoped sessions into general conversations", async () => {
    listSessionsMock.mockResolvedValue([
      session("geral", "cross_bula"),
      session("orfanada", "bula"),
      session("inconsistente", "cross_bula", "pdf"),
    ]);
    renderNavigation();
    const navigation = within(screen.getByRole("navigation", { name: "Conversas recentes" }));
    await navigation.findByText("Documento indisponível");
    expect(navigation.getAllByRole("link", { name: /Conversa geral/ })).toHaveLength(1);
    expect(
      navigation.queryByRole("link", { name: /Conversa orfanada|Conversa inconsistente/ })
    ).not.toBeInTheDocument();
  });

  it("shows a loading error separately from an empty history and permits retry", async () => {
    let hasFailure = true;
    listSessionsMock.mockImplementation(({ scope } = {}) => {
      if (scope === "bula" && hasFailure)
        return Promise.reject(new Error("Synthetic network failure"));
      return Promise.resolve([]);
    });
    const user = userEvent.setup();
    renderNavigation();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Não foi possível carregar suas conversas."
    );
    expect(screen.getAllByText("Nenhuma conversa recente.")).toHaveLength(1);
    hasFailure = false;
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    expect(screen.getAllByText("Nenhuma conversa recente.")).toHaveLength(2);
  });
});
