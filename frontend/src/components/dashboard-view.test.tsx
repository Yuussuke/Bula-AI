import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { listSystemBulas, type SystemBulaResponse } from "@/api/bulas";
import { DashboardView } from "@/components/dashboard-view";
import { ApiError } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

vi.mock("@/api/bulas", () => ({
  listSystemBulas: vi.fn(),
}));

const BULA_ID = "11111111-1111-4111-8111-111111111111";
const listSystemBulasMock = vi.mocked(listSystemBulas);

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

function buildSystemBula(overrides: Partial<SystemBulaResponse> = {}): SystemBulaResponse {
  return {
    id: BULA_ID,
    target_id: "amoxicilina-clavulanato-500mg-125mg-comprimido-ems",
    product_name: "AMOXICILINA + CLAVULANATO DE POTÁSSIO",
    active_ingredient: "amoxicilina + clavulanato de potássio",
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
    sha256_checksum: "f".repeat(64),
    content_size_bytes: 231137,
    ingestion_status: "ready",
    publication_state: "published",
    reviewed_by: "Allan Yuussuke Kita",
    reviewed_at: "2026-09-02T02:50:18Z",
    published_at: "2026-09-02T02:50:35Z",
    ...overrides,
  };
}

function LocationProbe(): ReactElement {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}</output>;
}

function renderDashboard(): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<DashboardView />} />
          <Route path="/bulas/:bulaId/chat" element={<p>Chat da bula</p>} />
        </Routes>
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  listSystemBulasMock.mockResolvedValue([buildSystemBula()]);
  useAuthStore.setState({
    user: {
      id: 5,
      email: "admin@bulaai.com",
      name: "Administrador Bula AI",
      role: "admin",
    },
    accessToken: "access-token",
    authResolved: true,
    isAuthenticated: true,
  });
});

describe("DashboardView system bula catalog", () => {
  it("shows a loading state while the authenticated catalog is requested", async () => {
    const deferredCatalog = createDeferredPromise<SystemBulaResponse[]>();
    listSystemBulasMock.mockReturnValue(deferredCatalog.promise);
    renderDashboard();

    const catalogLoadingState = screen.getByRole("status", { name: "Carregando catálogo" });
    expect(catalogLoadingState).toBeInTheDocument();
    expect(catalogLoadingState.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(
      20
    );
    expect(screen.getByRole("complementary")).toHaveClass("w-72", "shrink-0");

    await act(async () => {
      deferredCatalog.resolve([buildSystemBula()]);
      await deferredCatalog.promise;
    });

    expect(
      await within(screen.getByRole("main")).findByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO")
    ).toBeInTheDocument();
  });

  it("shows an actionable empty state when no published bula is available", async () => {
    listSystemBulasMock.mockResolvedValue([]);
    renderDashboard();

    expect(await screen.findByText("Nenhuma bula disponível")).toBeInTheDocument();
    expect(screen.getByText(/Ainda não existem bulas publicadas e prontas/)).toBeInTheDocument();
  });

  it("renders publication, ingestion and provenance separately", async () => {
    const user = userEvent.setup();
    renderDashboard();

    expect(await screen.findByText("Publicada")).toBeInTheDocument();
    expect(screen.getByText("Pronta")).toBeInTheDocument();
    expect(screen.getByText("EMS S/A")).toBeInTheDocument();
    expect(within(screen.getByRole("main")).getByText("500 mg + 125 mg")).toBeInTheDocument();

    const provenanceSummary = screen.getByText("Sobre esta bula");
    await user.click(provenanceSummary);

    expect(provenanceSummary.closest("details")).toHaveAttribute("open");
    expect(screen.getByText("102350532")).toBeInTheDocument();
    expect(screen.getByText("Bula do paciente")).toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: "Consultar esta bula no Bulário Eletrônico da ANVISA",
      })
    ).toHaveAttribute(
      "href",
      "https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=102350532"
    );
    expect(screen.queryByText("253510242290107")).not.toBeInTheDocument();
    expect(screen.queryByText(/Allan Yuussuke Kita/)).not.toBeInTheDocument();
  });

  it("filters the small catalog by accent-insensitive text and audience", async () => {
    const user = userEvent.setup();
    listSystemBulasMock.mockResolvedValue([
      buildSystemBula(),
      buildSystemBula({
        id: "22222222-2222-4222-8222-222222222222",
        product_name: "DIPIRONA MONOIDRATADA",
        active_ingredient: "dipirona monoidratada",
        manufacturer: "Sanofi Medley",
        audience: "professional",
      }),
    ]);
    renderDashboard();
    const catalogMain = screen.getByRole("main");

    const searchInput = await screen.findByRole("searchbox", {
      name: "Buscar no catálogo de bulas",
    });
    await user.type(searchInput, "potassio");

    expect(
      within(catalogMain).getByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO")
    ).toBeInTheDocument();
    expect(within(catalogMain).queryByText("DIPIRONA MONOIDRATADA")).not.toBeInTheDocument();

    await user.clear(searchInput);
    await user.selectOptions(screen.getByLabelText("Filtrar por público da bula"), "professional");

    expect(within(catalogMain).getByText("DIPIRONA MONOIDRATADA")).toBeInTheDocument();
    expect(
      within(catalogMain).queryByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO")
    ).not.toBeInTheDocument();
  });

  it("offers ready published bulas as shortcuts in the sidebar", async () => {
    const user = userEvent.setup();
    renderDashboard();

    const sidebar = screen.getByRole("navigation", { name: "Navegação principal" });
    const bulaShortcut = await within(sidebar).findByRole("link", {
      name: /Conversar sobre AMOXICILINA \+ CLAVULANATO DE POTÁSSIO, 500 mg \+ 125 mg/,
    });
    await user.click(bulaShortcut);

    expect(await screen.findByText("Chat da bula")).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent(`/bulas/${BULA_ID}/chat`);
  });

  it("opens the selected ready and published bula in its routed chat page", async () => {
    const user = userEvent.setup();
    renderDashboard();

    await user.click(await screen.findByRole("link", { name: "Conversar sobre esta bula" }));

    expect(await screen.findByText("Chat da bula")).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent(`/bulas/${BULA_ID}/chat`);
  });

  it("hides unpublished documents and disables a published document that is not ready", async () => {
    listSystemBulasMock.mockResolvedValue([
      buildSystemBula({
        id: "22222222-2222-4222-8222-222222222222",
        product_name: "BULA EM REVISÃO",
        publication_state: "vetted",
      }),
      buildSystemBula({
        product_name: "BULA EM PROCESSAMENTO",
        ingestion_status: "processing",
      }),
    ]);
    renderDashboard();

    expect(await screen.findByText("BULA EM PROCESSAMENTO")).toBeInTheDocument();
    expect(screen.queryByText("BULA EM REVISÃO")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Chat indisponível" })).toBeDisabled();
    expect(
      within(screen.getByRole("main")).getByText("Nenhuma bula pronta para conversa")
    ).toBeInTheDocument();
  });

  it("offers retry after a catalog request fails", async () => {
    const user = userEvent.setup();
    listSystemBulasMock
      .mockRejectedValueOnce(new Error("Backend unavailable"))
      .mockResolvedValueOnce([buildSystemBula()]);
    renderDashboard();

    expect(await screen.findByText("Não foi possível carregar o catálogo")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));

    expect(
      await within(screen.getByRole("main")).findByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO")
    ).toBeInTheDocument();
    expect(listSystemBulasMock).toHaveBeenCalledTimes(2);
  });

  it("explains when access to the catalog is denied", async () => {
    listSystemBulasMock.mockRejectedValue(new ApiError(403, "Forbidden"));
    renderDashboard();

    expect(await screen.findByText("Acesso ao catálogo não autorizado")).toBeInTheDocument();
    expect(
      screen.getByText(/Sua sessão expirou ou sua conta não possui acesso/)
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tentar novamente" })).not.toBeInTheDocument();
  });

  it("loads the authenticated catalog again after the dashboard is remounted", async () => {
    const firstDashboard = renderDashboard();
    expect(
      await within(screen.getByRole("main")).findByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO")
    ).toBeInTheDocument();

    firstDashboard.unmount();
    renderDashboard();

    expect(
      await within(screen.getByRole("main")).findByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO")
    ).toBeInTheDocument();
    expect(listSystemBulasMock).toHaveBeenCalledTimes(2);
  });
});
