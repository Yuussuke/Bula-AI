import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  listUserBulas,
  searchSystemBulas,
  type SystemBulaPage,
  type SystemBulaResponse,
} from "@/api/bulas";
import { listChatSessions } from "@/api/chat";
import { SystemBulaCatalog } from "@/components/bulas/system-bula-catalog";
import { UserBulaSection } from "@/components/bulas/user-bula-section";
import { DashboardView } from "@/components/dashboard-view";
import { ApiError } from "@/lib/api";
import { HomePage } from "@/pages/home-page";
import { useAuthStore } from "@/store/auth";

vi.mock("@/api/bulas", () => ({
  getBulaStatus: vi.fn(),
  searchSystemBulas: vi.fn(),
  listUserBulas: vi.fn(),
  uploadBula: vi.fn(),
}));

vi.mock("@/api/chat", () => ({ listChatSessions: vi.fn() }));

const BULA_ID = "11111111-1111-4111-8111-111111111111";
const searchSystemBulasMock = vi.mocked(searchSystemBulas);
const listUserBulasMock = vi.mocked(listUserBulas);

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
  return (
    <output data-testid="location">
      {location.pathname}
      {location.search}
    </output>
  );
}

function results(items: SystemBulaResponse[], total = items.length, offset = 0): SystemBulaPage {
  return { items, total, limit: 20, offset };
}

function renderDashboard(path = "/catalogo"): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<DashboardView />}>
            <Route index element={<HomePage />} />
            <Route path="/catalogo" element={<SystemBulaCatalog />} />
            <Route path="/minhas-bulas" element={<UserBulaSection />} />
          </Route>
          <Route path="/bulas/:bulaId/chat" element={<p>Chat da bula</p>} />
          <Route path="/chat" element={<p>Chat geral de teste</p>} />
        </Routes>
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  searchSystemBulasMock.mockResolvedValue(results([buildSystemBula()]));
  listUserBulasMock.mockResolvedValue([]);
  vi.mocked(listChatSessions).mockResolvedValue([]);
  useAuthStore.setState({
    user: { id: 5, email: "admin@bulaai.com", name: "Administrador Bula AI", role: "admin" },
    accessToken: "access-token",
    authResolved: true,
    isAuthenticated: true,
  });
});

describe("library navigation", () => {
  it("offers three destinations without downloading document lists on the home page", async () => {
    const user = userEvent.setup();
    renderDashboard("/");
    const main = within(screen.getByRole("main"));
    expect(main.getAllByRole("link")).toHaveLength(3);
    expect(searchSystemBulasMock).not.toHaveBeenCalled();
    expect(listUserBulasMock).not.toHaveBeenCalled();
    expect(
      within(screen.getByRole("navigation", { name: "Navegação principal" })).getAllByRole("link")
    ).toHaveLength(3);
    await user.click(main.getByRole("link", { name: /Catálogo ANVISA/ }));
    expect(await screen.findByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO")).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("/catalogo");
  });

  it("keeps private uploads on their own page", async () => {
    renderDashboard("/minhas-bulas");
    expect(await screen.findByText("Nenhuma bula enviada")).toBeInTheDocument();
    expect(screen.getByText(/Seus uploads são privados/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviar bula" })).toBeInTheDocument();
    expect(searchSystemBulasMock).not.toHaveBeenCalled();
  });
});

describe("server-paginated system catalog", () => {
  it("keeps controls together and clears search without redundant filter tags", async () => {
    const user = userEvent.setup();
    renderDashboard("/catalogo?q=amox&publico=patient&pagina=3");
    await screen.findByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO");
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Ordenar catálogo" }),
      "name_desc"
    );
    expect(searchSystemBulasMock).toHaveBeenLastCalledWith({
      query: "amox",
      audience: "patient",
      limit: 20,
      offset: 0,
      sort: "name_desc",
    });
    expect(screen.queryByLabelText("Filtros ativos")).not.toBeInTheDocument();
    await user.clear(screen.getByRole("searchbox"));
    await waitFor(() =>
      expect(searchSystemBulasMock).toHaveBeenLastCalledWith({
        query: "",
        audience: "patient",
        limit: 20,
        offset: 0,
        sort: "name_desc",
      })
    );
  });
  it("shows only one bounded page and supports next/previous navigation", async () => {
    const firstItems = Array.from({ length: 20 }, (_, index) =>
      buildSystemBula({ id: "first-" + index, product_name: "Produto " + index })
    );
    searchSystemBulasMock.mockImplementation(({ offset }) =>
      Promise.resolve(
        results(
          offset === 0 ? firstItems : [buildSystemBula({ product_name: "Segunda página" })],
          41,
          offset
        )
      )
    );
    const user = userEvent.setup();
    renderDashboard();
    expect(await screen.findByText("41 bulas encontradas")).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(20);
    expect(screen.getAllByText("Página 1 de 3")).toHaveLength(2);
    const topPagination = within(
      screen.getByRole("navigation", { name: "Paginação superior do catálogo" })
    );
    const bottomPagination = within(
      screen.getByRole("navigation", { name: "Paginação inferior do catálogo" })
    );
    expect(topPagination.getByRole("button", { name: "Anterior" })).toBeDisabled();
    expect(bottomPagination.getByRole("button", { name: "Anterior" })).toBeDisabled();
    await user.click(topPagination.getByRole("button", { name: "Próxima" }));
    expect(await screen.findByText("Segunda página")).toBeInTheDocument();
    expect(searchSystemBulasMock).toHaveBeenLastCalledWith({
      query: "",
      audience: "all",
      limit: 20,
      offset: 20,
    });
    expect(screen.getAllByText("Página 2 de 3")).toHaveLength(2);
    await user.click(
      within(screen.getByRole("navigation", { name: "Paginação inferior do catálogo" })).getByRole(
        "button",
        { name: "Anterior" }
      )
    );
    expect(await screen.findByText("Produto 0")).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(20);
  });

  it("searches the server and resets pagination instead of filtering the downloaded page", async () => {
    searchSystemBulasMock.mockImplementation(({ query, offset }) =>
      Promise.resolve(
        results(
          [buildSystemBula({ product_name: query ? "Resultado remoto" : "Página inicial" })],
          query ? 1 : 60,
          offset
        )
      )
    );
    const user = userEvent.setup();
    renderDashboard("/catalogo?pagina=2");
    await screen.findByText("Página inicial");
    await user.type(screen.getByRole("searchbox"), "termo alternativo");
    expect(await screen.findByText("Resultado remoto")).toBeInTheDocument();
    expect(screen.getByRole("searchbox")).toHaveFocus();
    expect(searchSystemBulasMock).toHaveBeenLastCalledWith({
      query: "termo alternativo",
      audience: "all",
      limit: 20,
      offset: 0,
    });
    expect(screen.getAllByText("Página 1 de 1")).toHaveLength(2);
    expect(screen.getByTestId("location")).toHaveTextContent("q=termo+alternativo");
    await user.selectOptions(screen.getByLabelText("Filtrar por público da bula"), "professional");
    await screen.findByText("Resultado remoto");
    expect(searchSystemBulasMock).toHaveBeenLastCalledWith({
      query: "termo alternativo",
      audience: "professional",
      limit: 20,
      offset: 0,
    });
  });

  it("restores filters and page from the URL", async () => {
    renderDashboard("/catalogo?q=potassio&publico=patient&pagina=3");
    await screen.findByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO");
    expect(searchSystemBulasMock).toHaveBeenCalledWith({
      query: "potassio",
      audience: "patient",
      limit: 20,
      offset: 40,
    });
    expect(screen.getByRole("searchbox")).toHaveValue("potassio");
    expect(screen.getByLabelText("Filtrar por público da bula")).toHaveValue("patient");
  });

  it("keeps missing metadata explicit and source details collapsed until requested", async () => {
    searchSystemBulasMock.mockResolvedValue(
      results([
        buildSystemBula({
          manufacturer: null,
          source_published_at: null,
          source_updated_at: null,
          reviewed_by: null,
          reviewed_at: null,
        }),
      ])
    );
    const user = userEvent.setup();
    renderDashboard();
    expect(await screen.findByText("Fabricante não informado")).toBeInTheDocument();
    const summary = screen.getByText("Detalhes e fonte");
    expect(summary.closest("details")).not.toHaveAttribute("open");
    await user.click(summary);
    expect(summary.closest("details")).toHaveAttribute("open");
    expect(screen.getByText("Não informado")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Consultar fonte na ANVISA" })).toHaveAttribute(
      "href",
      buildSystemBula().canonical_source_url
    );
  });

  it("opens a selected document in the individual chat", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await user.click(await screen.findByRole("link", { name: /Conversar sobre AMOXICILINA/ }));
    expect(await screen.findByText("Chat da bula")).toBeInTheDocument();
  });

  it("offers a first-page recovery for an out-of-range URL", async () => {
    searchSystemBulasMock.mockImplementation(({ offset }) =>
      Promise.resolve(results(offset ? [] : [buildSystemBula()], 1, offset))
    );
    const user = userEvent.setup();
    renderDashboard("/catalogo?pagina=99");
    expect(await screen.findByText("Esta página não tem resultados")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Voltar à primeira página" }));
    expect(await screen.findByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO")).toBeInTheDocument();
  });

  it("shows loading without rendering the full catalog", async () => {
    const deferred = createDeferredPromise<SystemBulaPage>();
    searchSystemBulasMock.mockReturnValue(deferred.promise);
    renderDashboard();
    expect(screen.getByRole("status", { name: "Carregando catálogo" })).toBeInTheDocument();
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
    await act(async () => {
      deferred.resolve(results([buildSystemBula()]));
      await deferred.promise;
    });
    expect(await screen.findByRole("article")).toBeInTheDocument();
  });

  it("distinguishes an empty catalog from an empty search", async () => {
    searchSystemBulasMock.mockResolvedValue(results([]));
    renderDashboard();
    expect(await screen.findByText("Nenhuma bula disponível")).toBeInTheDocument();
  });

  it("clears an unsuccessful search", async () => {
    searchSystemBulasMock.mockImplementation(({ query }) =>
      Promise.resolve(results(query ? [] : [buildSystemBula()]))
    );
    const user = userEvent.setup();
    renderDashboard("/catalogo?q=inexistente");
    expect(await screen.findByText("Nenhuma bula encontrada")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Limpar busca e filtros" }));
    expect(await screen.findByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO")).toBeInTheDocument();
    expect(screen.getByRole("searchbox")).toHaveValue("");
  });

  it("offers retry for a failed request", async () => {
    searchSystemBulasMock
      .mockRejectedValueOnce(new Error("Unavailable"))
      .mockResolvedValueOnce(results([buildSystemBula()]));
    const user = userEvent.setup();
    renderDashboard();
    expect(await screen.findByText("Não foi possível carregar o catálogo")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO")).toBeInTheDocument();
  });

  it("explains denied access without retrying it", async () => {
    searchSystemBulasMock.mockRejectedValue(new ApiError(403, "Forbidden"));
    renderDashboard();
    expect(await screen.findByText("Acesso ao catálogo não autorizado")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tentar novamente" })).not.toBeInTheDocument();
  });
});
