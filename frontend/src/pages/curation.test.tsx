import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  assignCurationRole,
  decideSharedBula,
  getCurationRoleHistory,
  getSharedBula,
  listCurationUsers,
  listSharedBulas,
  type SharedBula,
  submitSharedBula,
} from "@/api/curation";
import { CurationDetail } from "@/components/bulas/curation-detail";
import { CurationSubmissionForm } from "@/components/bulas/curation-submission-form";
import { CurationUsersPage } from "@/pages/curation-users-page";
import { SharedBulasPage } from "@/pages/shared-bulas-page";
import { type AuthUser, useAuthStore } from "@/store/auth";

vi.mock("@/api/curation", () => ({
  assignCurationRole: vi.fn(),
  decideSharedBula: vi.fn(),
  getSharedBula: vi.fn(),
  getCurationRoleHistory: vi.fn(),
  getSharedPdf: vi.fn(),
  listCurationUsers: vi.fn(),
  listSharedBulas: vi.fn(),
  submitSharedBula: vi.fn(),
}));

const document: SharedBula = {
  id: "11111111-1111-4111-8111-111111111111",
  product_name: "Documento sintético",
  manufacturer: null,
  presentation: null,
  strength: null,
  source_url: "https://fabricante.example/bula.pdf",
  source_description: "Fonte declarada",
  review_status: "pending",
  ingestion_status: "pending",
  is_available: false,
  version: 3,
  submitted_at: "2026-10-30T12:00:00Z",
  sha256_checksum: "a".repeat(64),
  content_size_bytes: 600,
  error_message: null,
  ingestion_job_id: null,
  submitted_by_id: 99,
  supersedes_bula_id: null,
};

function renderPage(element: ReactElement): ReturnType<typeof render> {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{element}</MemoryRouter>
    </QueryClientProvider>
  );
}

function authenticate(role: AuthUser["role"]): void {
  useAuthStore.getState().setAuth({
    accessToken: "synthetic-token",
    user: { id: 1, name: "Revisor", email: "reviewer@example.com", role },
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  authenticate("user");
  vi.mocked(listSharedBulas).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
  vi.mocked(getSharedBula).mockResolvedValue({ document, events: [] });
  vi.mocked(getCurationRoleHistory).mockResolvedValue([]);
});

describe("shared leaflet curation", () => {
  it("does not offer submission or review controls to a reader", async () => {
    renderPage(<SharedBulasPage />);
    await waitFor(() => expect(listSharedBulas).toHaveBeenCalledWith("public", "", "", 1));
    expect(screen.queryByText("Submeter uma bula para curadoria")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Abrir fila de curadoria" })).not.toBeInTheDocument();
  });

  it("blocks the review page before requesting pending documents", () => {
    renderPage(<SharedBulasPage review />);
    expect(screen.getByRole("alert")).toHaveTextContent("restrita");
    expect(listSharedBulas).not.toHaveBeenCalled();
  });

  it("lets a contributor track personal submissions without review access", async () => {
    authenticate("contributor");
    const user = userEvent.setup();
    renderPage(<SharedBulasPage />);
    expect(screen.getByText("Submeter uma bula para curadoria")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Minhas submissões" }));
    await waitFor(() => expect(listSharedBulas).toHaveBeenCalledWith("mine", "", "", 1));
    expect(screen.queryByRole("link", { name: "Abrir fila de curadoria" })).not.toBeInTheDocument();
  });

  it("submits the original file and declared origin without approving it", async () => {
    const user = userEvent.setup();
    vi.mocked(submitSharedBula).mockResolvedValue(document);
    renderPage(<CurationSubmissionForm />);
    await user.click(screen.getByText("Submeter uma bula para curadoria"));
    const file = new File(["%PDF-1.7 synthetic"], "original.pdf", { type: "application/pdf" });
    await user.upload(screen.getByLabelText("PDF original (até 10 MB)"), file);
    await user.type(screen.getByLabelText("Endereço da fonte"), document.source_url);
    await user.type(screen.getByLabelText("Nome do medicamento no PDF"), document.product_name);
    await user.type(
      screen.getByLabelText("Identificação e origem do documento"),
      "Fabricante identificado"
    );
    const form = screen.getByRole("form", { name: "Submissão de bula compartilhada" });
    expect(screen.getByLabelText<HTMLInputElement>("PDF original (até 10 MB)").files?.[0]).toBe(
      file
    );
    expect(screen.getByLabelText("Endereço da fonte")).toBeValid();
    expect(screen.getByLabelText("Identificação e origem do documento")).toBeValid();
    // jsdom does not reflect user-event's FileList in native required-file validation.
    fireEvent.submit(form);
    expect(await screen.findByRole("status")).toHaveTextContent("Submissão recebida");
    expect(submitSharedBula).toHaveBeenCalledWith(
      {
        file,
        source_url: document.source_url,
        source_description: "Fabricante identificado",
        product_name: document.product_name,
        manufacturer: null,
      },
      expect.any(String)
    );
    expect(decideSharedBula).not.toHaveBeenCalled();
  });

  it("requires an explicit check and reason, then sends the displayed revision", async () => {
    const user = userEvent.setup();
    vi.mocked(decideSharedBula).mockResolvedValue({
      ...document,
      review_status: "approved",
      version: 4,
    });
    renderPage(<CurationDetail id={document.id} canReview />);
    const approve = await screen.findByRole("button", { name: "Aprovar e processar" });
    expect(approve).toBeDisabled();
    await user.type(screen.getByLabelText("Parecer ou justificativa"), "Fonte e PDF conferidos.");
    expect(approve).toBeDisabled();
    await user.click(screen.getByRole("checkbox"));
    await user.click(approve);
    await waitFor(() =>
      expect(decideSharedBula).toHaveBeenCalledWith(
        document.id,
        "approve",
        {
          expected_version: 3,
          reason: "Fonte e PDF conferidos.",
          product_name: document.product_name,
          manufacturer: null,
          presentation: null,
          strength: null,
        },
        expect.any(String)
      )
    );
  });

  it("shows a conflict without retrying or inventing a decision", async () => {
    const user = userEvent.setup();
    vi.mocked(decideSharedBula).mockRejectedValue(
      new Error("A submissão mudou. Atualize a página.")
    );
    renderPage(<CurationDetail id={document.id} canReview />);
    await user.type(
      await screen.findByLabelText("Parecer ou justificativa"),
      "Fonte insuficiente."
    );
    await user.click(screen.getByRole("button", { name: "Rejeitar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("A submissão mudou");
    expect(decideSharedBula).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText("Parecer ou justificativa")).toHaveValue("Fonte insuficiente.");
  });

  it("does not render decision controls for public document details", async () => {
    renderPage(<CurationDetail id={document.id} canReview={false} />);
    await screen.findByRole("button", { name: "Carregar PDF original" });
    expect(screen.queryByLabelText("Parecer ou justificativa")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Aprovar e processar" })).not.toBeInTheDocument();
  });

  it("does not load account data for a non-administrator", () => {
    authenticate("reviewer");
    renderPage(<CurationUsersPage />);
    expect(screen.getByRole("alert")).toHaveTextContent("administrador");
    expect(listCurationUsers).not.toHaveBeenCalled();
  });

  it("loads the administrator assignment screen without changing roles automatically", async () => {
    authenticate("admin");
    vi.mocked(listCurationUsers).mockResolvedValue([
      { id: 7, name: "Profissional", email: "professional@example.com", role: "user" },
    ]);
    renderPage(<CurationUsersPage />);
    await screen.findByText("Profissional");
    expect(screen.getByRole("option", { name: "Curador" })).toBeInTheDocument();
    expect(assignCurationRole).not.toHaveBeenCalled();
  });

  it("records an administrator designation only after an explicit role and reason", async () => {
    authenticate("admin");
    const account: AuthUser = {
      id: 7,
      name: "Profissional",
      email: "professional@example.com",
      role: "user",
    };
    vi.mocked(listCurationUsers).mockResolvedValue([account]);
    vi.mocked(assignCurationRole).mockResolvedValue({ ...account, role: "reviewer" });
    const user = userEvent.setup();
    renderPage(<CurationUsersPage />);
    await user.selectOptions(await screen.findByRole("combobox", { name: "Perfil" }), "reviewer");
    expect(screen.getByRole("button", { name: "Salvar perfil" })).toBeDisabled();
    await user.type(
      screen.getByLabelText("Justificativa da designação"),
      "Profissional designado para curadoria."
    );
    await user.click(screen.getByRole("button", { name: "Salvar perfil" }));
    await waitFor(() =>
      expect(assignCurationRole).toHaveBeenCalledWith(
        account,
        "reviewer",
        "Profissional designado para curadoria.",
        expect.any(String)
      )
    );
  });

  it("identifies the submitter and prevents spending a review on one's own submission", async () => {
    authenticate("admin");
    vi.mocked(getSharedBula).mockResolvedValue({
      document: { ...document, submitted_by_id: 1 },
      events: [],
      submitted_by_name: "Revisor",
    });
    const user = userEvent.setup();
    renderPage(<CurationDetail id={document.id} canReview />);
    const approve = await screen.findByRole("button", { name: "Aprovar e processar" });
    expect(screen.getByText(/Você enviou este documento/)).toBeInTheDocument();
    await user.type(
      screen.getByLabelText("Parecer ou justificativa"),
      "Conferência própria indevida"
    );
    await user.click(screen.getByRole("checkbox"));
    expect(approve).toBeDisabled();
    expect(screen.getByRole("button", { name: "Rejeitar" })).toBeDisabled();
    expect(decideSharedBula).not.toHaveBeenCalled();
  });

  it.each([false, true])(
    "reuses a pending operation key only for an unchanged decision (edited=%s)",
    async (edited) => {
      const user = userEvent.setup();
      vi.mocked(decideSharedBula)
        .mockRejectedValueOnce(new Error("Falha de conexão"))
        .mockResolvedValue(document);
      renderPage(<CurationDetail id={document.id} canReview />);
      await user.type(
        await screen.findByLabelText("Parecer ou justificativa"),
        "Fonte insuficiente."
      );
      await user.click(screen.getByRole("button", { name: "Rejeitar" }));
      await screen.findByText("Falha de conexão");
      await waitFor(() => expect(screen.getByRole("button", { name: "Rejeitar" })).toBeEnabled());
      if (edited)
        await user.type(screen.getByLabelText("Parecer ou justificativa"), " Falta identificação.");
      await user.click(screen.getByRole("button", { name: "Rejeitar" }));
      await waitFor(() => expect(decideSharedBula).toHaveBeenCalledTimes(2));
      const calls = vi.mocked(decideSharedBula).mock.calls;
      if (edited) expect(calls[0][3]).not.toBe(calls[1][3]);
      else expect(calls[0][3]).toBe(calls[1][3]);
    }
  );

  it("refreshes the detail after asynchronous ingestion failure and offers recovery", async () => {
    vi.useFakeTimers();
    const processing = {
      ...document,
      review_status: "approved" as const,
      ingestion_status: "processing" as const,
      ingestion_job_id: 12,
    };
    vi.mocked(getSharedBula)
      .mockResolvedValueOnce({ document: processing, events: [] })
      .mockResolvedValue({
        document: {
          ...processing,
          ingestion_status: "failed",
          error_message: "Falha sintética no processamento",
        },
        events: [],
      });
    const view = renderPage(<CurationDetail id={document.id} canReview />);
    try {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1);
      });
      expect(
        screen.queryByRole("button", { name: "Reenfileirar ingestão" })
      ).not.toBeInTheDocument();
      await act(async () => {
        await vi.advanceTimersByTimeAsync(6100);
      });
      expect(screen.getByText("Falha sintética no processamento")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Reenfileirar ingestão" })).toBeInTheDocument();
    } finally {
      view.unmount();
      vi.useRealTimers();
    }
  });

  it("loads administrative role history only on request", async () => {
    authenticate("admin");
    const user = userEvent.setup();
    vi.mocked(listCurationUsers).mockResolvedValue([
      { id: 7, name: "Profissional", email: "professional@example.com", role: "reviewer" },
    ]);
    vi.mocked(getCurationRoleHistory).mockResolvedValue([
      {
        id: "audit-1",
        user_id: 7,
        actor_id: 1,
        actor_name: "Responsável anterior",
        actor_role: "admin",
        previous_role: "user",
        assigned_role: "reviewer",
        reason: "Designação registrada anteriormente.",
        operation_id: "operation-1",
        request_fingerprint: "a".repeat(64),
        created_at: "2026-10-30T12:00:00Z",
      },
    ]);
    renderPage(<CurationUsersPage />);
    await screen.findByText("Profissional");
    expect(getCurationRoleHistory).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Histórico de designações" }));
    expect(await screen.findByText("Designação registrada anteriormente.")).toBeInTheDocument();
    expect(screen.getByText(/Responsável anterior/)).toBeInTheDocument();
    expect(getCurationRoleHistory).toHaveBeenCalledWith(7, 1);
  });
});
