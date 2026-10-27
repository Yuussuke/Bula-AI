import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getBulaStatus,
  listUserBulas,
  updateBulaAlias,
  uploadBula,
  type UserBulaResponse,
} from "@/api/bulas";
import { UserBulaSection } from "@/components/bulas/user-bula-section";

vi.mock("@/api/bulas", async (importOriginal) => {
  const originalModule = await importOriginal<typeof import("@/api/bulas")>();
  return {
    ...originalModule,
    getBulaStatus: vi.fn(),
    listUserBulas: vi.fn(),
    uploadBula: vi.fn(),
    updateBulaAlias: vi.fn(),
  };
});

const BULA_ID = "11111111-1111-4111-8111-111111111111";
const getBulaStatusMock = vi.mocked(getBulaStatus);
const listUserBulasMock = vi.mocked(listUserBulas);
const uploadBulaMock = vi.mocked(uploadBula);

function buildUserBula(overrides: Partial<UserBulaResponse> = {}): UserBulaResponse {
  return {
    id: BULA_ID,
    user_id: 4,
    drug_name: "Dipirona",
    alias: null,
    manufacturer: "Sanofi Medley",
    file_url: null,
    file_address: "stored_objects/dipirona",
    qdrant_collection: null,
    status: "pending",
    error_message: null,
    corpus: "private",
    created_at: "2026-09-07T12:00:00Z",
    updated_at: "2026-09-07T12:00:00Z",
    ...overrides,
  };
}

function renderUserBulaSection(): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  function TestRoot(): ReactElement {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <UserBulaSection />
        </MemoryRouter>
      </QueryClientProvider>
    );
  }

  return render(<TestRoot />);
}

beforeEach(() => {
  vi.clearAllMocks();
  listUserBulasMock.mockResolvedValue([]);
  getBulaStatusMock.mockResolvedValue({
    id: BULA_ID,
    drug_name: "Dipirona",
    alias: null,
    manufacturer: "Sanofi Medley",
    status: "pending",
    error_message: null,
  });
});

describe("UserBulaSection", () => {
  it("saves and clears a personal alias without changing the official product name", async () => {
    const document = buildUserBula({ status: "ready" });
    listUserBulasMock.mockResolvedValue([document]);
    vi.mocked(updateBulaAlias).mockResolvedValue({ ...document, alias: "Remédio de casa" });
    const user = userEvent.setup();
    renderUserBulaSection();
    await user.click(await screen.findByRole("button", { name: "Editar apelido de Dipirona" }));
    await user.type(screen.getByRole("textbox", { name: "Apelido da bula" }), "Remédio de casa");
    await user.click(screen.getByRole("button", { name: "Salvar apelido" }));
    expect(await screen.findByRole("heading", { name: "Remédio de casa" })).toBeInTheDocument();
    expect(updateBulaAlias).toHaveBeenCalledWith(BULA_ID, "Remédio de casa");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByText(/Dipirona · Sanofi/)).toBeInTheDocument();

    vi.mocked(updateBulaAlias).mockResolvedValue(document);
    await user.click(screen.getByRole("button", { name: "Editar apelido de Remédio de casa" }));
    await user.clear(screen.getByRole("textbox", { name: "Apelido da bula" }));
    await user.click(screen.getByRole("button", { name: "Salvar apelido" }));
    expect(await screen.findByRole("heading", { name: "Dipirona" })).toBeInTheDocument();
    expect(updateBulaAlias).toHaveBeenLastCalledWith(BULA_ID, null);
  });

  it("preserves the draft and original alias when saving fails", async () => {
    listUserBulasMock.mockResolvedValue([buildUserBula({ status: "ready" })]);
    vi.mocked(updateBulaAlias).mockRejectedValue(new Error("Unavailable"));
    const user = userEvent.setup();
    renderUserBulaSection();
    await user.click(await screen.findByRole("button", { name: "Editar apelido de Dipirona" }));
    await user.type(screen.getByRole("textbox", { name: "Apelido da bula" }), "Meu rascunho");
    await user.click(screen.getByRole("button", { name: "Salvar apelido" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível salvar");
    expect(screen.getByRole("textbox", { name: "Apelido da bula" })).toHaveValue("Meu rascunho");
  });
  it("filters personal documents by alias and status without showing system sources", async () => {
    listUserBulasMock.mockResolvedValue([
      buildUserBula({ status: "ready", alias: "Remédio da mãe" }),
      buildUserBula({ id: "error-document", status: "error", drug_name: "Outro documento" }),
      buildUserBula({
        id: "system-document",
        corpus: "system",
        status: "ready",
        drug_name: "Documento do catálogo",
      }),
    ]);
    const user = userEvent.setup();
    renderUserBulaSection();
    expect(await screen.findByText("Remédio da mãe")).toBeInTheDocument();
    expect(screen.queryByText("Documento do catálogo")).not.toBeInTheDocument();
    await user.type(screen.getByRole("searchbox", { name: "Buscar nas minhas bulas" }), "mae");
    expect(screen.getByText("Remédio da mãe")).toBeInTheDocument();
    expect(screen.queryByText("Outro documento")).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Filtrar minhas bulas por estado"), "error");
    expect(screen.getByText("Nenhuma bula corresponde à busca.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Limpar filtros" }));
    expect(screen.getByText("Outro documento")).toBeInTheDocument();
  });

  it("bounds the number of personal cards per page", async () => {
    listUserBulasMock.mockResolvedValue(
      Array.from({ length: 13 }, (_, index) =>
        buildUserBula({ id: "private-" + index, status: "ready", drug_name: "Pessoal " + index })
      )
    );
    const user = userEvent.setup();
    renderUserBulaSection();
    expect(await screen.findByText("Página 1 de 2")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Conversar sobre esta bula/ })).toHaveLength(12);
    await user.click(screen.getByRole("button", { name: "Próxima" }));
    expect(screen.getAllByRole("link", { name: /Conversar sobre esta bula/ })).toHaveLength(1);
  });

  it("adds a real upload to the list immediately after the API accepts it", async () => {
    const user = userEvent.setup();
    const uploadedBula = buildUserBula({ alias: "Dipirona da mãe" });
    getBulaStatusMock.mockResolvedValue({
      id: BULA_ID,
      drug_name: uploadedBula.drug_name,
      alias: uploadedBula.alias,
      manufacturer: uploadedBula.manufacturer,
      status: uploadedBula.status,
      error_message: null,
    });
    uploadBulaMock.mockResolvedValue(uploadedBula);
    renderUserBulaSection();

    expect(await screen.findByText("Nenhuma bula enviada")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Enviar bula" }));
    await user.type(screen.getByLabelText("Nome personalizado (opcional)"), "Dipirona da mãe");
    const pdfFile = new File(["%PDF-1.7"], "dipirona.pdf", {
      type: "application/pdf",
    });
    await user.upload(screen.getByLabelText("Arquivo PDF"), pdfFile);
    const submitButton = screen.getByRole("button", { name: "Enviar PDF" });
    expect(submitButton).toBeEnabled();
    await user.click(submitButton);

    expect(uploadBulaMock).toHaveBeenCalledOnce();
    expect(uploadBulaMock.mock.calls[0][0]).toEqual({
      alias: "Dipirona da mãe",
      file: pdfFile,
    });
    expect(await screen.findByText("Dipirona da mãe", {}, { timeout: 3_000 })).toBeInTheDocument();
    expect(screen.getByText("Processando...")).toBeInTheDocument();
    expect(screen.queryByText("Nenhuma bula enviada")).not.toBeInTheDocument();
  });
});
