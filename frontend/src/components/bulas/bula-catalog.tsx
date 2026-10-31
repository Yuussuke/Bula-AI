import { AlertCircle, ChevronLeft, ChevronRight, RefreshCw } from "lucide-react";
import { type ReactElement, useRef } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { CatalogBulaCard } from "@/components/bulas/catalog-bula-card";
import {
  type AudienceFilter,
  CatalogFilters,
  type CatalogSort,
} from "@/components/bulas/catalog-filters";
import { CatalogSelector } from "@/components/bulas/catalog-selector";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { usePublicCatalog } from "@/hooks/use-public-catalog";
import { ApiError, SessionExpiredError } from "@/lib/api";
import {
  CATALOG_SCOPES,
  catalogParameters,
  type CatalogScope,
  readCatalogScope,
} from "@/lib/catalog-scope";

const PAGE_SIZE = 20;

export function BulaCatalog(): ReactElement {
  const titleRef = useRef<HTMLHeadingElement>(null);
  const [parameters, setParameters] = useSearchParams();
  const searchTerm = parameters.get("q") ?? "";
  const catalogScope = readCatalogScope(parameters.get("catalogo"));
  const audienceValue = parameters.get("publico");
  const sort: CatalogSort = parameters.get("ordem") === "za" ? "name_desc" : "name_asc";
  const audience: AudienceFilter =
    catalogScope === "system" && (audienceValue === "patient" || audienceValue === "professional")
      ? audienceValue
      : "all";
  const requestedPage = Number(parameters.get("pagina") ?? 1);
  const page =
    Number.isSafeInteger(requestedPage) &&
    requestedPage > 0 &&
    requestedPage <= Math.floor(Number.MAX_SAFE_INTEGER / PAGE_SIZE)
      ? requestedPage
      : 1;
  const catalogQuery = usePublicCatalog({
    catalog_scope: catalogScope,
    query: searchTerm,
    audience,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
    ...(sort === "name_desc" ? { sort } : {}),
  });
  const items = catalogQuery.data?.items ?? [];
  const total = catalogQuery.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const hasFilters = searchTerm.length > 0 || audience !== "all";

  const navigateToResults = (
    query: string,
    targetAudience: AudienceFilter,
    targetPage = 1,
    targetSort: CatalogSort = sort,
    targetCatalogScope: CatalogScope = catalogScope
  ): void => {
    const next = catalogParameters(targetCatalogScope);
    if (query) next.set("q", query);
    if (targetAudience !== "all") next.set("publico", targetAudience);
    if (targetPage > 1) next.set("pagina", String(targetPage));
    if (targetSort === "name_desc") next.set("ordem", "za");
    setParameters(next);
    if (targetPage !== page) titleRef.current?.scrollIntoView?.({ block: "start" });
  };

  const isAccessDenied =
    catalogQuery.error instanceof SessionExpiredError ||
    (catalogQuery.error instanceof ApiError && catalogQuery.error.status === 403);
  return (
    <section className="space-y-5" aria-labelledby="system-catalog-title">
      <div className="space-y-2">
        <h1
          ref={titleRef}
          id="system-catalog-title"
          className="text-2xl font-semibold tracking-tight"
        >
          {CATALOG_SCOPES[catalogScope]}
        </h1>
        <p className="text-muted-foreground text-sm">
          Pesquise no catálogo e confira o fabricante, a concentração e a apresentação antes de
          conversar.
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <CatalogSelector
          value={catalogScope}
          onChange={(selected) => navigateToResults(searchTerm, "all", 1, sort, selected)}
        />
        <Button asChild variant="outline" size="sm">
          <Link to={`/chat?${catalogParameters(catalogScope).toString()}`}>
            Conversar com este catálogo
          </Link>
        </Button>
      </div>
      <CatalogFilters
        key={catalogScope}
        showAudience={catalogScope === "system"}
        searchTerm={searchTerm}
        audience={audience}
        sort={sort}
        onSearch={(query, selectedAudience, selectedSort) =>
          navigateToResults(query, selectedAudience, 1, selectedSort)
        }
      />
      {catalogQuery.isLoading ? (
        <div role="status" aria-label="Carregando catálogo" className="space-y-3">
          {Array.from({ length: 5 }, (_, index) => (
            <Skeleton key={index} className="h-24 w-full" />
          ))}
        </div>
      ) : null}
      {catalogQuery.isError ? (
        <Alert variant="destructive">
          <AlertCircle aria-hidden="true" />
          <AlertTitle>
            {isAccessDenied
              ? "Acesso ao catálogo não autorizado"
              : "Não foi possível carregar o catálogo"}
          </AlertTitle>
          <AlertDescription>
            <p>
              {isAccessDenied
                ? "Sua sessão expirou ou sua conta não possui acesso a este conteúdo. Entre novamente."
                : "Verifique a conexão com o servidor e tente novamente."}
            </p>
            {!isAccessDenied ? (
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={() => void catalogQuery.refetch()}
              >
                <RefreshCw aria-hidden="true" className="mr-2 h-4 w-4" />
                Tentar novamente
              </Button>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}
      {catalogQuery.isSuccess ? (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p role="status" className="text-muted-foreground flex flex-wrap gap-x-3 text-sm">
              <span>{total === 1 ? "1 bula encontrada" : `${total} bulas encontradas`}</span>
              {items.length > 0 ? (
                <span>
                  Mostrando {(page - 1) * PAGE_SIZE + 1}–{(page - 1) * PAGE_SIZE + items.length}
                </span>
              ) : null}
            </p>
            {total > 0 ? (
              <CatalogPagination
                position="superior"
                page={page}
                pageCount={pageCount}
                onPageChange={(nextPage) => navigateToResults(searchTerm, audience, nextPage)}
              />
            ) : null}
          </div>
          {items.length > 0 ? (
            <div className="divide-y overflow-hidden rounded-xl border">
              {items.map((bula) => (
                <CatalogBulaCard key={bula.id} bula={bula} />
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed p-10 text-center">
              <h2 className="font-medium">
                {total > 0
                  ? "Esta página não tem resultados"
                  : hasFilters
                    ? "Nenhuma bula encontrada"
                    : "Nenhuma bula disponível"}
              </h2>
              <p className="text-muted-foreground mt-2 text-sm">
                {total > 0
                  ? "Volte à primeira página para consultar os resultados disponíveis."
                  : hasFilters
                    ? "Tente outro nome, princípio ativo, fabricante ou concentração."
                    : "Ainda não existem bulas publicadas e prontas para consulta no catálogo."}
              </p>
              {hasFilters || page > 1 ? (
                <Button
                  variant="outline"
                  className="mt-4"
                  onClick={() =>
                    navigateToResults(page > 1 ? searchTerm : "", page > 1 ? audience : "all")
                  }
                >
                  {page > 1 ? "Voltar à primeira página" : "Limpar busca e filtros"}
                </Button>
              ) : null}
            </div>
          )}
          {total > 0 ? (
            <CatalogPagination
              position="inferior"
              page={page}
              pageCount={pageCount}
              onPageChange={(nextPage) => navigateToResults(searchTerm, audience, nextPage)}
            />
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function CatalogPagination({
  position,
  page,
  pageCount,
  onPageChange,
}: {
  position: "superior" | "inferior";
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
}): ReactElement {
  return (
    <nav
      aria-label={`Paginação ${position} do catálogo`}
      className="flex flex-wrap items-center justify-between gap-3"
    >
      <span className="text-muted-foreground text-sm">
        Página {page} de {pageCount}
      </span>
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="outline"
          disabled={page === 1}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft aria-hidden="true" className="mr-1 h-4 w-4" />
          Anterior
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={page >= pageCount}
          onClick={() => onPageChange(page + 1)}
        >
          Próxima
          <ChevronRight aria-hidden="true" className="ml-1 h-4 w-4" />
        </Button>
      </div>
    </nav>
  );
}
