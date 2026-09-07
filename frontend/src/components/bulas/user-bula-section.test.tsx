import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getBulaStatus, listUserBulas, uploadBula, type UserBulaResponse } from "@/api/bulas";
import { UserBulaSection } from "@/components/bulas/user-bula-section";

vi.mock("@/api/bulas", async (importOriginal) => {
  const originalModule = await importOriginal<typeof import("@/api/bulas")>();
  return {
    ...originalModule,
    getBulaStatus: vi.fn(),
    listUserBulas: vi.fn(),
    uploadBula: vi.fn(),
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
        <UserBulaSection />
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
    status: "pending",
    error_message: null,
  });
});

describe("UserBulaSection", () => {
  it("adds a real upload to the list immediately after the API accepts it", async () => {
    const user = userEvent.setup();
    const uploadedBula = buildUserBula();
    uploadBulaMock.mockResolvedValue(uploadedBula);
    renderUserBulaSection();

    expect(await screen.findByText("Nenhuma bula enviada")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Enviar bula" }));
    await user.type(screen.getByLabelText("Nome do medicamento"), "Dipirona");
    await user.type(screen.getByLabelText("Fabricante (opcional)"), "Sanofi Medley");
    const pdfFile = new File(["%PDF-1.7"], "dipirona.pdf", {
      type: "application/pdf",
    });
    await user.upload(screen.getByLabelText("Arquivo PDF"), pdfFile);
    const submitButton = screen.getByRole("button", { name: "Enviar PDF" });
    expect(submitButton).toBeEnabled();
    await user.click(submitButton);

    expect(uploadBulaMock).toHaveBeenCalledOnce();
    expect(uploadBulaMock.mock.calls[0][0]).toEqual({
      drugName: "Dipirona",
      manufacturer: "Sanofi Medley",
      file: pdfFile,
    });
    expect(await screen.findByText("Dipirona", {}, { timeout: 3_000 })).toBeInTheDocument();
    expect(screen.getByText("Processando...")).toBeInTheDocument();
    expect(screen.queryByText("Nenhuma bula enviada")).not.toBeInTheDocument();
  });
});
