import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import {
  listUserBulas,
  type PublicCatalogBulaResponse,
  type PublicCatalogPage,
  searchPublicCatalog,
} from "@/api/bulas";
import { listChatSessions } from "@/api/chat";
import { BulaCatalog } from "@/components/bulas/bula-catalog";
import { UserBulaSection } from "@/components/bulas/user-bula-section";
import { DashboardView } from "@/components/dashboard-view";
import { ApiError } from "@/lib/api";
import { HomePage } from "@/pages/home-page";
import { useAuthStore } from "@/store/auth";

vi.mock("@/api/bulas", () => ({
  getBulaStatus: vi.fn(),
  searchPublicCatalog: vi.fn(),
  listUserBulas: vi.fn(),
  uploadBula: vi.fn(),
}));

vi.mock("@/api/chat", () => ({ listChatSessions: vi.fn() }));

const BULA_ID = "11111111-1111-4111-8111-111111111111";
const searchPublicCatalogMock = vi.mocked(searchPublicCatalog);
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

function buildSystemBula(
  overrides: Partial<PublicCatalogBulaResponse> = {}
): PublicCatalogBulaResponse {
  return {
    id: BULA_ID,
    corpus: "system",
    is_available: true,
    product_name: "AMOXICILINA + CLAVULANATO DE POTÁSSIO",
    active_ingredient: "amoxicilina + clavulanato de potássio",
    strength: "500 mg + 125 mg",
    pharmaceutical_form: "comprimido revestido",
    presentation: "embalagem com 12 unidades",
    audience: "patient",
    manufacturer: "EMS S/A",
    registration_number: "102350532",
    source_url: "https://consultas.anvisa.gov.br/api/consulta/bulario",
    source_published_at: "2026-02-25T17:20:51Z",
    source_updated_at: "2026-08-26T03:00:00Z",
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

function results(
  items: PublicCatalogBulaResponse[],
  total = items.length,
  offset = 0
): PublicCatalogPage {
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
            <Route path="/catalogo" element={<BulaCatalog />} />
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

beforeAll(() => {
  Object.defineProperties(HTMLElement.prototype, {
    hasPointerCapture: { configurable: true, value: () => false },
    setPointerCapture: { configurable: true, value: () => undefined },
    releasePointerCapture: { configurable: true, value: () => undefined },
    scrollIntoView: { configurable: true, value: () => undefined },
  });
});

beforeEach(() => {
  vi.clearAllMocks();
  searchPublicCatalogMock.mockResolvedValue(results([buildSystemBula()]));
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
  it("makes a saved medication conversation discoverable from the home sidebar", async () => {
    vi.mocked(listChatSessions).mockImplementation(({ scope } = {}) =>
      Promise.resolve(
        scope === "bula"
          ? [
              {
                id: "saved-session",
                user_id: 5,
                bula_id: BULA_ID,
                scope: "bula",
                title: "Dúvida sobre losartana",
                created_at: "2026-10-25T10:00:00Z",
                updated_at: "2026-10-26T10:00:00Z",
                messages: [],
              },
            ]
          : []
      )
    );
    const user = userEvent.setup();
    renderDashboard("/");
    const savedConversation = await screen.findByRole("link", { name: /Dúvida sobre losartana/ });
    expect(savedConversation).toHaveAttribute(
      "href",
      `/bulas/${BULA_ID}/chat?session=saved-session`
    );
    await user.click(savedConversation);
    expect(await screen.findByText("Chat da bula")).toBeInTheDocument();
    expect(searchPublicCatalogMock).not.toHaveBeenCalled();
  });

  it("offers three destinations without downloading document lists on the home page", async () => {
    const user = userEvent.setup();
    renderDashboard("/");
    const main = within(screen.getByRole("main"));
    expect(main.getAllByRole("link")).toHaveLength(3);
    expect(searchPublicCatalogMock).not.toHaveBeenCalled();
    expect(listUserBulasMock).not.toHaveBeenCalled();
    expect(
      within(screen.getByRole("navigation", { name: "Navegação principal" })).getAllByRole("link")
    ).toHaveLength(6);
    await user.click(main.getByRole("link", { name: /Catálogo Geral/ }));
    expect(await screen.findByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO")).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("/catalogo");
  });

  it("keeps private uploads on their own page", async () => {
    renderDashboard("/minhas-bulas");
    expect(await screen.findByText("Nenhuma bula enviada")).toBeInTheDocument();
    expect(screen.getByText(/Seus uploads são privados/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviar bula" })).toBeInTheDocument();
    expect(searchPublicCatalogMock).not.toHaveBeenCalled();
  });
});

describe("server-paginated system catalog", () => {
  it("keeps controls together and clears search without redundant filter tags", async () => {
    const user = userEvent.setup();
    renderDashboard("/catalogo?catalogo=system&q=amox&publico=patient&pagina=3");
    await screen.findByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO");
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Ordenar catálogo" }),
      "name_desc"
    );
    expect(searchPublicCatalogMock).toHaveBeenLastCalledWith({
      catalog_scope: "system",
      query: "amox",
      audience: "patient",
      limit: 20,
      offset: 0,
      sort: "name_desc",
    });
    expect(screen.queryByLabelText("Filtros ativos")).not.toBeInTheDocument();
    await user.clear(screen.getByRole("searchbox"));
    await waitFor(() =>
      expect(searchPublicCatalogMock).toHaveBeenLastCalledWith({
        catalog_scope: "system",
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
    searchPublicCatalogMock.mockImplementation(({ offset }) =>
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
    expect(searchPublicCatalogMock).toHaveBeenLastCalledWith({
      catalog_scope: "all",
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
    searchPublicCatalogMock.mockImplementation(({ query, offset }) =>
      Promise.resolve(
        results(
          [buildSystemBula({ product_name: query ? "Resultado remoto" : "Página inicial" })],
          query ? 1 : 60,
          offset
        )
      )
    );
    const user = userEvent.setup();
    renderDashboard("/catalogo?catalogo=system&pagina=2");
    await screen.findByText("Página inicial");
    await user.type(screen.getByRole("searchbox"), "termo alternativo");
    expect(await screen.findByText("Resultado remoto")).toBeInTheDocument();
    expect(screen.getByRole("searchbox")).toHaveFocus();
    expect(searchPublicCatalogMock).toHaveBeenLastCalledWith({
      catalog_scope: "system",
      query: "termo alternativo",
      audience: "all",
      limit: 20,
      offset: 0,
    });
    expect(screen.getAllByText("Página 1 de 1")).toHaveLength(2);
    expect(screen.getByTestId("location")).toHaveTextContent("q=termo+alternativo");
    await user.selectOptions(screen.getByLabelText("Filtrar por público da bula"), "professional");
    await screen.findByText("Resultado remoto");
    expect(searchPublicCatalogMock).toHaveBeenLastCalledWith({
      catalog_scope: "system",
      query: "termo alternativo",
      audience: "professional",
      limit: 20,
      offset: 0,
    });
  });

  it("restores filters and page from the URL", async () => {
    renderDashboard("/catalogo?catalogo=system&q=potassio&publico=patient&pagina=3");
    await screen.findByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO");
    expect(searchPublicCatalogMock).toHaveBeenCalledWith({
      catalog_scope: "system",
      query: "potassio",
      audience: "patient",
      limit: 20,
      offset: 40,
    });
    expect(screen.getByRole("searchbox")).toHaveValue("potassio");
    expect(screen.getByLabelText("Filtrar por público da bula")).toHaveValue("patient");
  });

  it("keeps missing metadata explicit and source details collapsed until requested", async () => {
    searchPublicCatalogMock.mockResolvedValue(
      results([
        buildSystemBula({
          manufacturer: null,
          source_published_at: null,
          source_updated_at: null,
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
      buildSystemBula().source_url
    );
  });

  it("opens a selected document in the individual chat", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await user.click(await screen.findByRole("link", { name: /Conversar sobre AMOXICILINA/ }));
    expect(await screen.findByText("Chat da bula")).toBeInTheDocument();
  });

  it("offers a first-page recovery for an out-of-range URL", async () => {
    searchPublicCatalogMock.mockImplementation(({ offset }) =>
      Promise.resolve(results(offset ? [] : [buildSystemBula()], 1, offset))
    );
    const user = userEvent.setup();
    renderDashboard("/catalogo?pagina=99");
    expect(await screen.findByText("Esta página não tem resultados")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Voltar à primeira página" }));
    expect(await screen.findByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO")).toBeInTheDocument();
  });

  it("shows loading without rendering the full catalog", async () => {
    const deferred = createDeferredPromise<PublicCatalogPage>();
    searchPublicCatalogMock.mockReturnValue(deferred.promise);
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
    searchPublicCatalogMock.mockResolvedValue(results([]));
    renderDashboard();
    expect(await screen.findByText("Nenhuma bula disponível")).toBeInTheDocument();
  });

  it("clears an unsuccessful search", async () => {
    searchPublicCatalogMock.mockImplementation(({ query }) =>
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
    searchPublicCatalogMock
      .mockRejectedValueOnce(new Error("Unavailable"))
      .mockResolvedValueOnce(results([buildSystemBula()]));
    const user = userEvent.setup();
    renderDashboard();
    expect(await screen.findByText("Não foi possível carregar o catálogo")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("AMOXICILINA + CLAVULANATO DE POTÁSSIO")).toBeInTheDocument();
  });

  it("explains denied access without retrying it", async () => {
    searchPublicCatalogMock.mockRejectedValue(new ApiError(403, "Forbidden"));
    renderDashboard();
    expect(await screen.findByText("Acesso ao catálogo não autorizado")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tentar novamente" })).not.toBeInTheDocument();
  });
});

describe("public catalog source boundary", () => {
  it("restores shared scope and keeps unknown metadata explicit", async () => {
    searchPublicCatalogMock.mockResolvedValue(
      results([
        buildSystemBula({
          corpus: "shared",
          audience: null,
          registration_number: null,
          active_ingredient: null,
          pharmaceutical_form: null,
          source_url: "https://source.example/leaflet.pdf",
        }),
      ])
    );
    renderDashboard("/catalogo?catalogo=shared&pagina=2&publico=patient");
    await screen.findByRole("article");
    expect(searchPublicCatalogMock).toHaveBeenCalledWith({
      catalog_scope: "shared",
      query: "",
      audience: "all",
      limit: 20,
      offset: 20,
    });
    expect(screen.queryByLabelText("Filtrar por público da bula")).not.toBeInTheDocument();
    expect(screen.getByText("Compartilhada")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Conversar com este catálogo" })).toHaveAttribute(
      "href",
      "/chat?catalogo=shared"
    );
    expect(screen.getByRole("link", { name: "Consultar fonte original" })).toHaveAttribute(
      "href",
      "https://source.example/leaflet.pdf"
    );
  });

  it("changes catalog and resets pagination and audience without losing search", async () => {
    const user = userEvent.setup();
    renderDashboard("/catalogo?catalogo=system&q=amox&publico=patient&pagina=3");
    await screen.findByRole("article");
    await user.click(screen.getByRole("combobox", { name: "Catálogo consultado" }));
    await user.click(screen.getByRole("option", { name: "Catálogo Compartilhado" }));
    await waitFor(() =>
      expect(searchPublicCatalogMock).toHaveBeenLastCalledWith({
        catalog_scope: "shared",
        query: "amox",
        audience: "all",
        limit: 20,
        offset: 0,
      })
    );
    expect(screen.getByTestId("location")).toHaveTextContent("/catalogo?catalogo=shared&q=amox");
  });
});
