import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  type ChatSessionResponse,
  deleteChatSession,
  listChatSessions,
  renameChatSession,
  setChatSessionPinned,
} from "@/api/chat";
import { RecentConversations } from "@/components/chat/recent-conversations";

vi.mock("@/api/chat", () => ({
  listChatSessions: vi.fn(),
  renameChatSession: vi.fn(),
  deleteChatSession: vi.fn(),
  setChatSessionPinned: vi.fn(),
}));
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
  it("moves pinned chats above recent chats and restores them when unpinned", async () => {
    let isPinned = false;
    listSessionsMock.mockImplementation((options = {}) => {
      const current = { ...session("geral", "cross_bula"), is_pinned: isPinned };
      return Promise.resolve(
        Boolean(options.isPinned) === isPinned && (!options.scope || options.scope === "cross_bula")
          ? [current]
          : []
      );
    });
    vi.mocked(setChatSessionPinned).mockImplementation((id, nextPinned) => {
      isPinned = nextPinned;
      return Promise.resolve({ ...session(id, "cross_bula"), is_pinned: isPinned });
    });
    const user = userEvent.setup();
    renderNavigation();
    expect(screen.queryByText("Fixados")).not.toBeInTheDocument();
    await user.click(
      await screen.findByRole(
        "button",
        { name: "Opções da conversa Conversa geral" },
        { timeout: 3000 }
      )
    );
    expect(screen.getAllByRole("menuitem")).toHaveLength(3);
    await user.click(screen.getByRole("menuitem", { name: "Fixar" }));
    await screen.findByText("Fixados");
    expect(screen.getAllByRole("link", { name: /Conversa geral/ })).toHaveLength(1);
    expect(setChatSessionPinned).toHaveBeenCalledWith("geral", true);
    await user.click(
      await screen.findByRole("button", { name: "Opções da conversa Conversa geral" })
    );
    await user.click(screen.getByRole("menuitem", { name: "Desafixar" }));
    await waitFor(() => expect(screen.queryByText("Fixados")).not.toBeInTheDocument());
    expect(await screen.findByRole("link", { name: /Conversa geral/ })).toBeVisible();
    expect(setChatSessionPinned).toHaveBeenCalledWith("geral", false);
  });

  it("leaves a chat in place when pinning fails", async () => {
    vi.mocked(setChatSessionPinned).mockRejectedValue(new Error("Synthetic outage"));
    const user = userEvent.setup();
    renderNavigation();
    await user.click(
      await screen.findByRole("button", { name: "Opções da conversa Conversa geral" })
    );
    await user.click(screen.getByRole("menuitem", { name: "Fixar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Não foi possível alterar a fixação"
    );
    expect(screen.queryByText("Fixados")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Conversa geral/ })).toBeVisible();
  });
  it("renames a conversation and refreshes its visible title", async () => {
    let title = "Conversa geral";
    listSessionsMock.mockImplementation(({ scope } = {}) =>
      Promise.resolve(scope === "cross_bula" ? [{ ...session("geral", "cross_bula"), title }] : [])
    );
    vi.mocked(renameChatSession).mockImplementation((id, nextTitle) => {
      title = nextTitle;
      return Promise.resolve({ ...session(id, "cross_bula"), title });
    });
    const user = userEvent.setup();
    renderNavigation();
    await user.click(
      await screen.findByRole("button", { name: "Opções da conversa Conversa geral" })
    );
    await user.click(screen.getByRole("menuitem", { name: "Renomear" }));
    const dialog = screen.getByRole("dialog", { name: "Renomear conversa" });
    const input = within(dialog).getByLabelText("Nome da conversa");
    await user.clear(input);
    await user.type(input, "  Minhas dúvidas  ");
    await user.click(within(dialog).getByRole("button", { name: "Salvar" }));
    expect(await screen.findByRole("link", { name: /Minhas dúvidas/ })).toBeVisible();
    expect(renameChatSession).toHaveBeenCalledWith("geral", "Minhas dúvidas");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(deleteChatSession).not.toHaveBeenCalled();
  });

  it("preserves the rename draft and permits a manual retry after an error", async () => {
    vi.mocked(renameChatSession)
      .mockRejectedValueOnce(new Error("Synthetic outage"))
      .mockResolvedValueOnce({ ...session("geral", "cross_bula"), title: "Meu nome" });
    const user = userEvent.setup();
    renderNavigation();
    await user.click(
      await screen.findByRole("button", { name: "Opções da conversa Conversa geral" })
    );
    await user.click(screen.getByRole("menuitem", { name: "Renomear" }));
    const input = screen.getByLabelText("Nome da conversa");
    await user.clear(input);
    await user.type(input, "Meu nome");
    await user.click(screen.getByRole("button", { name: "Salvar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível salvar o nome");
    expect(input).toHaveValue("Meu nome");
    expect(renameChatSession).toHaveBeenCalledOnce();
    await user.click(screen.getByRole("button", { name: "Salvar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(renameChatSession).toHaveBeenCalledTimes(2);
  });

  it("requires confirmation and clears only the deleted conversation's cache", async () => {
    let isDeleted = false;
    listSessionsMock.mockImplementation(({ scope } = {}) =>
      Promise.resolve(
        scope === "cross_bula"
          ? isDeleted
            ? []
            : [session("geral", "cross_bula")]
          : [session("losartana", "bula", "pdf-losartana")]
      )
    );
    vi.mocked(deleteChatSession).mockImplementation(() => {
      isDeleted = true;
      return Promise.resolve({ session_id: "geral" });
    });
    const user = userEvent.setup();
    const startNew = vi.fn();
    const client = renderNavigation({
      context: { scope: "cross_bula" },
      currentSessionId: "geral",
      onStartNewSession: startNew,
    });
    client.setQueryData(["chat-session", "cross_bula:all", "geral"], { sessionId: "geral" });
    client.setQueryData(["chat-session", "bula:pdf-losartana", "losartana"], {
      sessionId: "losartana",
    });
    await user.click(
      await screen.findByRole("button", { name: "Opções da conversa Conversa geral" })
    );
    await user.click(screen.getByRole("menuitem", { name: "Excluir" }));
    expect(screen.getByRole("alertdialog", { name: "Excluir conversa?" })).toBeVisible();
    expect(deleteChatSession).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.getByRole("link", { name: /Conversa geral/ })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Opções da conversa Conversa geral" }));
    await user.click(screen.getByRole("menuitem", { name: "Excluir" }));
    await user.click(screen.getByRole("button", { name: "Excluir conversa" }));
    await waitFor(() =>
      expect(screen.queryByRole("link", { name: /Conversa geral/ })).not.toBeInTheDocument()
    );
    expect(screen.getByRole("link", { name: /Conversa losartana/ })).toBeVisible();
    expect(client.getQueryData(["chat-session", "cross_bula:all", "geral"])).toBeUndefined();
    expect(client.getQueryData(["chat-session", "bula:pdf-losartana", "losartana"])).toBeDefined();
    expect(startNew).toHaveBeenCalledOnce();
  });

  it("keeps a conversation when deletion fails", async () => {
    vi.mocked(deleteChatSession).mockRejectedValueOnce(new Error("Synthetic outage"));
    const user = userEvent.setup();
    renderNavigation();
    await user.click(
      await screen.findByRole("button", { name: "Opções da conversa Conversa geral" })
    );
    await user.click(screen.getByRole("menuitem", { name: "Excluir" }));
    await user.click(screen.getByRole("button", { name: "Excluir conversa" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível excluir");
    expect(deleteChatSession).toHaveBeenCalledOnce();
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.getByRole("link", { name: /Conversa geral/ })).toBeVisible();
  });

  it("allows managing orphaned history and disables only a conversation being processed", async () => {
    listSessionsMock.mockImplementation(({ scope } = {}) =>
      Promise.resolve(
        scope === "cross_bula" ? [session("geral", "cross_bula")] : [session("orfanada", "bula")]
      )
    );
    const user = userEvent.setup();
    renderNavigation({ currentSessionId: "geral", isCurrentSessionBusy: true });
    expect(
      await screen.findByRole("button", { name: "Opções da conversa Conversa geral" })
    ).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Opções da conversa Conversa orfanada" }));
    expect(screen.getByRole("menuitem", { name: "Renomear" })).toBeVisible();
    expect(screen.getByRole("menuitem", { name: "Excluir" })).toBeVisible();
  });
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
      isPinned: false,
      limit: 10,
      offset: 0,
      sort: "updated_at",
    });
    expect(listSessionsMock).toHaveBeenCalledWith({
      scope: "cross_bula",
      isPinned: false,
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
      isPinned: false,
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
