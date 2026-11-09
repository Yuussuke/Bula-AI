import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ChatSessionResponse, getChatSession, listChatSessions } from "@/api/chat";
import { HomePage } from "@/pages/home-page";
import { useAuthStore } from "@/store/auth";

vi.mock("@/api/chat", () => ({ listChatSessions: vi.fn(), getChatSession: vi.fn() }));

const listSessionsMock = vi.mocked(listChatSessions);
const getSessionMock = vi.mocked(getChatSession);

function session(overrides: Partial<ChatSessionResponse> = {}): ChatSessionResponse {
  return {
    id: "latest-chat",
    user_id: 1,
    bula_id: null,
    scope: "cross_bula",
    catalog_scope: "shared",
    title: "Minha última conversa",
    created_at: "2026-11-07T12:00:00Z",
    updated_at: "2026-11-08T12:00:00Z",
    messages: [],
    ...overrides,
  };
}

function renderHome(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  useAuthStore.setState({
    user: { id: 1, name: "Allan Kita", email: "review@example.test", role: "user" },
  });
  listSessionsMock.mockImplementation((options) =>
    Promise.resolve(options?.isPinned ? [] : [session()])
  );
  getSessionMock.mockResolvedValue(session());
});

describe("home workspace", () => {
  it("shows pinned conversations below recent conversations with separate server filters", async () => {
    listSessionsMock.mockImplementation((options) =>
      Promise.resolve(
        options?.isPinned
          ? [session({ id: "pinned", title: "Conversa importante", is_pinned: true })]
          : [session({ title: "Conversa recente", is_pinned: false })]
      )
    );
    renderHome();
    const recent = screen.getByRole("region", { name: "Conversas recentes" });
    const pinned = screen.getByRole("region", { name: "Conversas fixadas" });
    expect(
      await within(recent).findByRole("link", { name: /Continuar conversa Conversa recente/ })
    ).toBeVisible();
    expect(
      await within(pinned).findByRole("link", { name: /Continuar conversa Conversa importante/ })
    ).toBeVisible();
    expect(within(recent).queryByText("Conversa importante")).not.toBeInTheDocument();
    expect(recent.compareDocumentPosition(pinned) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(listSessionsMock).toHaveBeenCalledWith({ limit: 3, sort: "updated_at", isPinned: true });
  });

  it("omits the pinned section when there are no pinned conversations", async () => {
    renderHome();
    await screen.findByRole("link", { name: /Continuar conversa Minha última/ });
    expect(screen.queryByRole("heading", { name: "Conversas fixadas" })).not.toBeInTheDocument();
  });

  it("shows three recent conversations with their own document and catalog links", async () => {
    listSessionsMock.mockImplementation((options) =>
      Promise.resolve(
        options?.isPinned
          ? []
          : [
              session(),
              session({
                id: "individual",
                title: "Conversa da bula",
                scope: "bula",
                bula_id: "leaflet-id",
              }),
              session({ id: "official", title: "Conversa ANVISA", catalog_scope: "system" }),
            ]
      )
    );
    renderHome();
    expect(screen.getByRole("heading", { name: "Conversas recentes" })).toBeVisible();
    expect(await screen.findAllByRole("link", { name: /Continuar conversa/ })).toHaveLength(3);
    expect(
      screen.getByRole("link", { name: "Continuar conversa Conversa da bula" })
    ).toHaveAttribute("href", "/bulas/leaflet-id/chat?session=individual");
    expect(
      screen.getByRole("link", { name: "Continuar conversa Conversa ANVISA" })
    ).toHaveAttribute("href", "/chat?catalogo=system&session=official");
    expect(listSessionsMock).toHaveBeenCalledWith({
      limit: 3,
      sort: "updated_at",
      isPinned: false,
    });
  });

  it("offers the main actions and continues the latest chat in its original catalog", async () => {
    getSessionMock.mockResolvedValue(
      session({
        messages: [
          {
            id: "question",
            session_id: "latest-chat",
            role: "user",
            content: "Qual é a temperatura de conservação?",
            retrieval_mode: null,
            source_chunks: [],
            created_at: "2026-11-08T12:00:00Z",
            updated_at: "2026-11-08T12:00:00Z",
          },
        ],
      })
    );
    renderHome();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Olá, Allan.");
    expect(screen.getByRole("link", { name: "Iniciar conversa" })).toHaveAttribute("href", "/chat");
    expect(screen.getByRole("link", { name: /Catálogo Geral/ })).toHaveAttribute(
      "href",
      "/catalogo"
    );
    expect(screen.getByRole("link", { name: /Minhas bulas/ })).toHaveAttribute(
      "href",
      "/minhas-bulas"
    );
    expect(
      await screen.findByRole("link", { name: /Continuar conversa Minha última/ })
    ).toHaveAttribute("href", "/chat?catalogo=shared&session=latest-chat");
    expect(await screen.findByText("Qual é a temperatura de conservação?")).toBeVisible();
  });

  it("opens a legacy individual conversation under its own leaflet", async () => {
    listSessionsMock.mockImplementation((options) =>
      Promise.resolve(
        options?.isPinned ? [] : [session({ scope: undefined, bula_id: "leaflet-id" })]
      )
    );
    renderHome();
    expect(
      await screen.findByRole("link", { name: /Continuar conversa Minha última/ })
    ).toHaveAttribute("href", "/bulas/leaflet-id/chat?session=latest-chat");
  });

  it("marks a deleted leaflet as unavailable without offering to continue it", async () => {
    listSessionsMock.mockImplementation((options) =>
      Promise.resolve(options?.isPinned ? [] : [session({ scope: "bula", bula_id: null })])
    );
    renderHome();
    expect(await screen.findByText("Documento indisponível")).toBeVisible();
    expect(screen.queryByRole("link", { name: /Continuar conversa/ })).not.toBeInTheDocument();
    expect(getSessionMock).not.toHaveBeenCalled();
  });

  it("shows an honest empty state when the user has no conversations", async () => {
    listSessionsMock.mockResolvedValue([]);
    renderHome();
    expect(await screen.findByText(/Suas próximas conversas aparecerão aqui/)).toBeVisible();
    expect(screen.queryByRole("link", { name: /Continuar conversa/ })).not.toBeInTheDocument();
  });

  it("allows retrying a history failure while the main actions remain available", async () => {
    listSessionsMock.mockRejectedValueOnce(new Error("Unavailable"));
    const user = userEvent.setup();
    renderHome();
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível carregar");
    expect(screen.getByRole("link", { name: "Iniciar conversa" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(
      await screen.findByRole("link", { name: /Continuar conversa Minha última/ })
    ).toBeVisible();
  });

  it("keeps the session link usable when its optional message preview fails", async () => {
    getSessionMock.mockRejectedValue(new Error("Preview unavailable"));
    renderHome();
    expect(
      await screen.findByRole("link", { name: /Continuar conversa Minha última/ })
    ).toBeVisible();
  });
});
