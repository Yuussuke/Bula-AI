import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { getSystemBula, type SystemBulaResponse } from "@/api/bulas";
import {
  askBulaQuestion,
  type AskResponse,
  type ChatSessionResponse,
  continueChatSession,
  getChatSession,
  listChatSessions,
} from "@/api/chat";
import { ApiError } from "@/lib/api";
import { ChatPage } from "@/pages/chat-page";

vi.mock("@/api/bulas", () => ({
  getSystemBula: vi.fn(),
}));

vi.mock("@/api/chat", () => ({
  askBulaQuestion: vi.fn(),
  continueChatSession: vi.fn(),
  getChatSession: vi.fn(),
  listChatSessions: vi.fn(),
}));

const BULA_ID = "11111111-1111-4111-8111-111111111111";
const OTHER_BULA_ID = "33333333-3333-4333-8333-333333333333";
const SESSION_ID = "22222222-2222-4222-8222-222222222222";

const SYSTEM_BULA: SystemBulaResponse = {
  id: BULA_ID,
  target_id: "amoxicilina-clavulanato-500mg-125mg-comprimido-ems",
  product_name: "AMOXICILINA + CLAVULANATO DE POTASSIO",
  active_ingredient: "amoxicilina + clavulanato de potassio",
  strength: "500 mg + 125 mg",
  pharmaceutical_form: "comprimido revestido",
  presentation: "embalagem com 12 unidades",
  audience: "patient",
  manufacturer: "EMS S/A",
  company_tax_id: "57507378000365",
  anvisa_product_id: 124891,
  registration_number: "102350532",
  process_number: "253510242290107",
  expedition_number: "0186508263",
  transaction_number: "2551962026",
  source_record_id: "35934920",
  canonical_source_url: "https://consultas.anvisa.gov.br/api/consulta/bulario",
  source_published_at: "2026-02-25T17:20:51Z",
  source_updated_at: "2026-08-26T03:00:00Z",
  sha256_checksum: "ffd3780e4895c67b9bf1986127e4a205265245f865b6b0123843400582689d41",
  content_size_bytes: 231137,
  ingestion_status: "ready",
  publication_state: "published",
  reviewed_by: "Reviewer",
  reviewed_at: "2026-09-02T02:50:18Z",
  published_at: "2026-09-02T02:50:35Z",
};

const FIRST_RESPONSE: AskResponse = {
  session_id: SESSION_ID,
  answer: "Este medicamento e indicado para tratar infeccoes descritas na bula.",
  source_chunks: [
    {
      section_title: "INDICACOES",
      chunk_text: "Trecho recuperado da bula para fundamentar a resposta.",
      relevance_score: 0.92,
    },
  ],
};

const getSystemBulaMock = vi.mocked(getSystemBula);
const askBulaQuestionMock = vi.mocked(askBulaQuestion);
const continueChatSessionMock = vi.mocked(continueChatSession);
const getChatSessionMock = vi.mocked(getChatSession);
const listChatSessionsMock = vi.mocked(listChatSessions);
const scrollIntoViewMock = vi.fn();

interface DeferredPromise<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
}

function createDeferredPromise<T>(): DeferredPromise<T> {
  let resolvePromise!: (value: T) => void;
  const promise = new Promise<T>((resolve) => {
    resolvePromise = resolve;
  });

  return { promise, resolve: resolvePromise };
}

function buildPersistedSession(bulaId = BULA_ID): ChatSessionResponse {
  return {
    id: SESSION_ID,
    user_id: 4,
    bula_id: bulaId,
    title: "Para que serve este medicamento?",
    created_at: "2026-09-04T01:00:00Z",
    updated_at: "2026-09-04T01:01:00Z",
    messages: [
      {
        id: "44444444-4444-4444-8444-444444444444",
        session_id: SESSION_ID,
        role: "user",
        content: "Para que serve este medicamento?",
        retrieval_mode: "dense",
        source_chunks: [],
        created_at: "2026-09-04T01:00:00Z",
        updated_at: "2026-09-04T01:00:00Z",
      },
      {
        id: "55555555-5555-4555-8555-555555555555",
        session_id: SESSION_ID,
        role: "assistant",
        content: "Resposta persistida no PostgreSQL.",
        retrieval_mode: "dense",
        source_chunks: FIRST_RESPONSE.source_chunks,
        created_at: "2026-09-04T01:01:00Z",
        updated_at: "2026-09-04T01:01:00Z",
      },
    ],
  };
}

function LocationProbe(): ReactElement {
  const location = useLocation();
  return <output data-testid="location">{`${location.pathname}${location.search}`}</output>;
}

function renderChatPage(initialEntry = `/bulas/${BULA_ID}/chat`): void {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/bulas/:bulaId/chat" element={<ChatPage />} />
          <Route path="/" element={<p>Dashboard</p>} />
        </Routes>
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
    configurable: true,
    value: scrollIntoViewMock,
  });
});

beforeEach(() => {
  vi.clearAllMocks();
  getSystemBulaMock.mockResolvedValue(SYSTEM_BULA);
  askBulaQuestionMock.mockResolvedValue(FIRST_RESPONSE);
  continueChatSessionMock.mockResolvedValue({
    session_id: SESSION_ID,
    answer: "Resposta contextual para a pergunta seguinte.",
    source_chunks: [],
  });
  getChatSessionMock.mockResolvedValue(buildPersistedSession());
  listChatSessionsMock.mockResolvedValue([
    { ...buildPersistedSession(), messages: [] },
    {
      ...buildPersistedSession(OTHER_BULA_ID),
      id: "66666666-6666-4666-8666-666666666666",
      title: "Conversa de outra bula",
      messages: [],
    },
  ]);
});

describe("ChatPage", () => {
  it("keeps the final page structure reserved while the conversation loads", async () => {
    const deferredBula = createDeferredPromise<SystemBulaResponse>();
    getSystemBulaMock.mockReturnValue(deferredBula.promise);
    renderChatPage();

    const loadingState = screen.getByRole("status", { name: "Carregando conversa" });
    expect(loadingState.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(10);
    expect(screen.getByRole("complementary")).toHaveClass("w-72", "shrink-0");

    await act(async () => {
      deferredBula.resolve(SYSTEM_BULA);
      await deferredBula.promise;
    });

    expect(
      await screen.findByRole("heading", { name: SYSTEM_BULA.product_name })
    ).toBeInTheDocument();
  });

  it("loads the bula header and identifies the exact retrieval mode", async () => {
    renderChatPage();

    expect(
      await screen.findByRole("heading", { name: SYSTEM_BULA.product_name })
    ).toBeInTheDocument();
    expect(screen.getByText("Dense retrieval (beta)")).toBeInTheDocument();
    expect(screen.getByRole("complementary")).toHaveClass("w-72", "shrink-0");
    expect(getSystemBulaMock).toHaveBeenCalledWith(BULA_ID);
    expect(getChatSessionMock).not.toHaveBeenCalled();
  });

  it("starts the first turn without reloading and stores the session in the URL", async () => {
    const user = userEvent.setup();
    renderChatPage();
    const questionInput = await screen.findByRole("textbox", {
      name: "Digite sua pergunta sobre a bula",
    });
    const scrollCallCountBeforeSend = scrollIntoViewMock.mock.calls.length;

    await user.type(questionInput, "Para que serve este medicamento?");
    await user.keyboard("{Enter}");

    expect(await screen.findByText(FIRST_RESPONSE.answer)).toBeInTheDocument();
    expect(
      within(screen.getByRole("log", { name: "Histórico da conversa" })).getByText(
        "Para que serve este medicamento?"
      )
    ).toBeInTheDocument();
    expect(askBulaQuestionMock).toHaveBeenCalledWith(BULA_ID, {
      question: "Para que serve este medicamento?",
      retrieval_mode: "dense",
    });
    expect(continueChatSessionMock).not.toHaveBeenCalled();
    expect(screen.getByTestId("location")).toHaveTextContent(
      `/bulas/${BULA_ID}/chat?session=${SESSION_ID}`
    );
    expect(scrollIntoViewMock.mock.calls.length).toBeGreaterThan(scrollCallCountBeforeSend);
  });

  it("lists only sessions from the current bula and opens the selected conversation", async () => {
    const user = userEvent.setup();
    renderChatPage();

    const sessionLink = await screen.findByRole("link", {
      name: /Para que serve este medicamento\?/,
    });
    expect(screen.queryByText("Conversa de outra bula")).not.toBeInTheDocument();

    await user.click(sessionLink);

    expect(await screen.findByText("Resposta persistida no PostgreSQL.")).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent(
      `/bulas/${BULA_ID}/chat?session=${SESSION_ID}`
    );
  });

  it("starts a new conversation from an existing session", async () => {
    const user = userEvent.setup();
    renderChatPage(`/bulas/${BULA_ID}/chat?session=${SESSION_ID}`);
    expect(await screen.findByText("Resposta persistida no PostgreSQL.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Nova conversa" }));

    expect(screen.getByTestId("location")).toHaveTextContent(`/bulas/${BULA_ID}/chat`);
    expect(screen.queryByText("Resposta persistida no PostgreSQL.")).not.toBeInTheDocument();
    expect(screen.getByText("Converse sobre esta bula")).toBeInTheDocument();
  });

  it("announces loading and blocks another send while the answer is pending", async () => {
    const deferredResponse = createDeferredPromise<AskResponse>();
    askBulaQuestionMock.mockReturnValue(deferredResponse.promise);
    const user = userEvent.setup();
    renderChatPage();
    const questionInput = await screen.findByRole("textbox", {
      name: "Digite sua pergunta sobre a bula",
    });

    await user.type(questionInput, "Qual e a indicacao?");
    await user.click(screen.getByRole("button", { name: "Enviar pergunta" }));

    const optimisticUserMessage = await screen.findByRole("article", {
      name: "Mensagem de Você",
    });
    expect(optimisticUserMessage).toHaveTextContent("Qual e a indicacao?");
    expect(optimisticUserMessage).not.toHaveTextContent("Enviando…");
    expect(optimisticUserMessage).toHaveClass("chat-message-enter");
    expect(questionInput).toHaveValue("");

    const loadingText = await screen.findByText(/Bula AI está preparando a resposta/);
    expect(loadingText.closest('[role="status"]')).toBeInTheDocument();
    expect(questionInput).toBeDisabled();
    expect(screen.getByRole("button", { name: "Enviar pergunta" })).toBeDisabled();
    expect(askBulaQuestionMock).toHaveBeenCalledOnce();

    await act(async () => {
      deferredResponse.resolve(FIRST_RESPONSE);
      await deferredResponse.promise;
    });

    expect(await screen.findByText(FIRST_RESPONSE.answer)).toBeInTheDocument();
    expect(screen.getByRole("article", { name: "Mensagem de Você" })).toHaveTextContent(
      "Qual e a indicacao?"
    );
  });

  it("ignores a duplicate submit while the same question is in flight", async () => {
    const deferredResponse = createDeferredPromise<AskResponse>();
    askBulaQuestionMock.mockReturnValue(deferredResponse.promise);
    const user = userEvent.setup();
    renderChatPage();
    const questionInput = await screen.findByRole("textbox", {
      name: "Digite sua pergunta sobre a bula",
    });
    const composerForm = questionInput.closest("form");
    if (!composerForm) {
      throw new Error("Chat composer form was not rendered.");
    }

    await user.type(questionInput, "Qual é a indicação?");
    fireEvent.submit(composerForm);
    fireEvent.submit(composerForm);

    await waitFor(() => {
      expect(askBulaQuestionMock).toHaveBeenCalledOnce();
    });

    await act(async () => {
      deferredResponse.resolve(FIRST_RESPONSE);
      await deferredResponse.promise;
    });
  });

  it("keeps source chunks collapsed until the user expands them", async () => {
    const user = userEvent.setup();
    renderChatPage();
    const questionInput = await screen.findByRole("textbox", {
      name: "Digite sua pergunta sobre a bula",
    });

    await user.type(questionInput, "Mostre a fonte");
    await user.keyboard("{Enter}");

    const sourceButton = await screen.findByRole("button", { name: "Ver 1 fonte na bula" });
    expect(sourceButton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText(FIRST_RESPONSE.source_chunks[0].chunk_text)).not.toBeInTheDocument();

    await user.click(sourceButton);

    expect(sourceButton).toHaveAttribute("aria-expanded", "true");
    expect(await screen.findByText(FIRST_RESPONSE.source_chunks[0].chunk_text)).toBeInTheDocument();
    expect(screen.getByText(FIRST_RESPONSE.source_chunks[0].section_title)).toBeInTheDocument();
  });

  it("renders assistant Markdown while keeping user Markdown as plain text", async () => {
    askBulaQuestionMock.mockResolvedValue({
      ...FIRST_RESPONSE,
      answer: "Use com ** atencao **.\n\n- Leia a bula\n- Procure orientacao profissional",
    });
    const user = userEvent.setup();
    renderChatPage();
    const questionInput = await screen.findByRole("textbox", {
      name: "Digite sua pergunta sobre a bula",
    });

    await user.type(questionInput, "Explique **sem formatar**");
    await user.keyboard("{Enter}");

    const assistantMessage = await screen.findByRole("article", { name: "Mensagem de Bula AI" });
    expect(within(assistantMessage).getByText("atencao").tagName).toBe("STRONG");
    expect(within(assistantMessage).getByRole("list")).toBeInTheDocument();
    expect(screen.getByText("Explique **sem formatar**")).toBeInTheDocument();
  });

  it("restores source chunks when a persisted conversation is reopened", async () => {
    const user = userEvent.setup();
    renderChatPage(`/bulas/${BULA_ID}/chat?session=${SESSION_ID}`);

    const sourceButton = await screen.findByRole("button", { name: "Ver 1 fonte na bula" });
    await user.click(sourceButton);

    expect(await screen.findByText(FIRST_RESPONSE.source_chunks[0].chunk_text)).toBeInTheDocument();
  });

  it("preserves the question when sending fails so the user can retry", async () => {
    askBulaQuestionMock.mockRejectedValue(new ApiError(503, "Service unavailable"));
    const user = userEvent.setup();
    renderChatPage();
    const questionInput = await screen.findByRole("textbox", {
      name: "Digite sua pergunta sobre a bula",
    });

    await user.type(questionInput, "Posso usar durante a gravidez?");
    await user.click(screen.getByRole("button", { name: "Enviar pergunta" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível enviar");
    expect(screen.getByRole("article", { name: "Mensagem de Você" })).toHaveTextContent(
      "Não foi possível enviar"
    );
    expect(questionInput).toHaveValue("Posso usar durante a gravidez?");
    expect(questionInput).toBeEnabled();
  });

  it("restores a persisted session from the URL and continues that session", async () => {
    const user = userEvent.setup();
    renderChatPage(`/bulas/${BULA_ID}/chat?session=${SESSION_ID}`);

    expect(await screen.findByText("Resposta persistida no PostgreSQL.")).toBeInTheDocument();
    expect(screen.getByText("Para que serve este medicamento?")).toBeInTheDocument();
    expect(getChatSessionMock).toHaveBeenCalledWith(SESSION_ID);

    const questionInput = screen.getByRole("textbox", {
      name: "Digite sua pergunta sobre a bula",
    });
    await user.type(questionInput, "E para criancas?");
    await user.keyboard("{Enter}");

    expect(
      await screen.findByText("Resposta contextual para a pergunta seguinte.")
    ).toBeInTheDocument();
    expect(continueChatSessionMock).toHaveBeenCalledWith(SESSION_ID, {
      question: "E para criancas?",
      retrieval_mode: "dense",
    });
    expect(askBulaQuestionMock).not.toHaveBeenCalled();
  });

  it("blocks a session whose bula does not match the route", async () => {
    getChatSessionMock.mockResolvedValue(buildPersistedSession(OTHER_BULA_ID));
    renderChatPage(`/bulas/${BULA_ID}/chat?session=${SESSION_ID}`);

    expect(await screen.findByRole("heading", { name: "Chat indisponível" })).toBeInTheDocument();
    expect(screen.getByText(/Esta conversa pertence a outra bula/)).toBeInTheDocument();
    expect(
      screen.queryByRole("textbox", { name: "Digite sua pergunta sobre a bula" })
    ).not.toBeInTheDocument();
    await waitFor(() => {
      expect(getChatSessionMock).toHaveBeenCalledWith(SESSION_ID);
    });
  });
});
