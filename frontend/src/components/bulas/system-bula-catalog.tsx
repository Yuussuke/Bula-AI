import { AlertCircle, FileSearch, RefreshCw } from "lucide-react";
import { type ReactElement, useMemo, useState } from "react";

import { type SystemBulaResponse } from "@/api/bulas";
import { SystemBulaCard } from "@/components/bulas/system-bula-card";
import { type AudienceFilter, SystemBulaFilters } from "@/components/bulas/system-bula-filters";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useSystemBulas } from "@/hooks/use-system-bulas";
import { ApiError, SessionExpiredError } from "@/lib/api";

function normalizeSearchValue(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pt-BR")
    .trim();
}

function matchesSearchTerm(bula: SystemBulaResponse, normalizedSearchTerm: string): boolean {
  if (!normalizedSearchTerm) {
    return true;
  }

  const searchableValues = [
    bula.product_name,
    bula.active_ingredient,
    bula.manufacturer,
    bula.strength,
    bula.pharmaceutical_form,
  ];

  return searchableValues.some((value) =>
    normalizeSearchValue(value).includes(normalizedSearchTerm)
  );
}

function CatalogLoadingState(): ReactElement {
  return (
    <section role="status" aria-label="Carregando catálogo" className="space-y-5">
      <span className="sr-only">Carregando catálogo de bulas…</span>

      <div className="space-y-2">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-4 w-full max-w-xl" />
      </div>

      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_14.5rem]">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>

      <Skeleton className="h-4 w-32" />

      <div className="grid items-stretch gap-5 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }, (_, index) => (
          <div key={index} className="border-border bg-card rounded-xl border p-5">
            <div className="flex gap-2">
              <Skeleton className="h-6 w-20" />
              <Skeleton className="h-6 w-16" />
            </div>
            <Skeleton className="mt-5 h-6 w-4/5" />
            <Skeleton className="mt-2 h-4 w-2/5" />
            <div className="mt-7 space-y-4">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-4/5" />
              <Skeleton className="h-4 w-3/5" />
              <Skeleton className="h-10 w-full" />
            </div>
            <Skeleton className="mt-7 h-10 w-full" />
          </div>
        ))}
      </div>
    </section>
  );
}

interface EmptyCatalogStateProps {
  hasActiveFilters: boolean;
  onClearFilters: () => void;
}

function EmptyCatalogState({
  hasActiveFilters,
  onClearFilters,
}: EmptyCatalogStateProps): ReactElement {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center py-16 text-center">
        <div className="bg-muted mb-4 flex h-14 w-14 items-center justify-center rounded-full">
          <FileSearch aria-hidden="true" className="text-muted-foreground h-7 w-7" />
        </div>
        <h2 className="text-lg font-semibold">
          {hasActiveFilters ? "Nenhuma bula encontrada" : "Nenhuma bula disponível"}
        </h2>
        <p className="text-muted-foreground mt-2 max-w-lg text-sm">
          {hasActiveFilters
            ? "Tente buscar por outro medicamento, princípio ativo ou fabricante."
            : "Ainda não existem bulas publicadas e prontas para consulta no catálogo."}
        </p>
        {hasActiveFilters ? (
          <Button type="button" variant="outline" className="mt-5" onClick={onClearFilters}>
            Limpar busca e filtros
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function SystemBulaCatalog(): ReactElement {
  const [searchTerm, setSearchTerm] = useState("");
  const [audience, setAudience] = useState<AudienceFilter>("all");
  const catalogQuery = useSystemBulas();

  const publishedBulas = useMemo(
    () => (catalogQuery.data ?? []).filter((bula) => bula.publication_state === "published"),
    [catalogQuery.data]
  );
  const filteredBulas = useMemo(() => {
    const normalizedSearchTerm = normalizeSearchValue(searchTerm);

    return publishedBulas.filter((bula) => {
      const matchesAudience = audience === "all" || bula.audience === audience;
      return matchesAudience && matchesSearchTerm(bula, normalizedSearchTerm);
    });
  }, [audience, publishedBulas, searchTerm]);
  const hasActiveFilters = searchTerm.trim().length > 0 || audience !== "all";
  const hasReadyBula = publishedBulas.some((bula) => bula.ingestion_status === "ready");

  const clearFilters = (): void => {
    setSearchTerm("");
    setAudience("all");
  };

  if (catalogQuery.isLoading) {
    return <CatalogLoadingState />;
  }

  if (catalogQuery.isError) {
    const isAccessDenied =
      catalogQuery.error instanceof SessionExpiredError ||
      (catalogQuery.error instanceof ApiError && catalogQuery.error.status === 403);

    return (
      <Alert variant="destructive">
        <AlertCircle aria-hidden="true" />
        <AlertTitle>
          {isAccessDenied
            ? "Acesso ao catálogo não autorizado"
            : "Não foi possível carregar o catálogo"}
        </AlertTitle>
        <AlertDescription className="flex flex-col items-start gap-3">
          <span>
            {isAccessDenied
              ? "Sua sessão expirou ou sua conta não possui acesso a este conteúdo. Entre novamente."
              : "Verifique a conexão com o servidor e tente novamente."}
          </span>
          {!isAccessDenied ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => void catalogQuery.refetch()}
            >
              <RefreshCw aria-hidden="true" className="h-3.5 w-3.5" />
              Tentar novamente
            </Button>
          ) : null}
        </AlertDescription>
      </Alert>
    );
  }

  if (publishedBulas.length === 0) {
    return <EmptyCatalogState hasActiveFilters={false} onClearFilters={clearFilters} />;
  }

  return (
    <section aria-labelledby="system-catalog-title" className="space-y-5">
      <div className="space-y-1">
        <h2 id="system-catalog-title" className="text-xl font-semibold">
          Bulas verificadas
        </h2>
        <p className="text-muted-foreground text-sm">
          Escolha uma bula publicada para conversar com o Bula AI usando o conteúdo oficial.
        </p>
      </div>

      <SystemBulaFilters
        searchTerm={searchTerm}
        audience={audience}
        onSearchTermChange={setSearchTerm}
        onAudienceChange={setAudience}
      />

      {!hasReadyBula ? (
        <Alert>
          <AlertCircle aria-hidden="true" />
          <AlertTitle>Nenhuma bula pronta para conversa</AlertTitle>
          <AlertDescription>
            As bulas publicadas ainda estão sendo processadas ou precisam de atenção.
          </AlertDescription>
        </Alert>
      ) : null}

      <p className="text-muted-foreground text-sm" role="status">
        {filteredBulas.length === 1
          ? "1 bula encontrada"
          : `${filteredBulas.length} bulas encontradas`}
      </p>

      {filteredBulas.length === 0 ? (
        <EmptyCatalogState hasActiveFilters={hasActiveFilters} onClearFilters={clearFilters} />
      ) : (
        <div className="grid items-stretch gap-5 md:grid-cols-2 xl:grid-cols-3">
          {filteredBulas.map((bula) => (
            <SystemBulaCard key={bula.id} bula={bula} />
          ))}
        </div>
      )}
    </section>
  );
}
