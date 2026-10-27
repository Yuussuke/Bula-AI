import { AlertCircle, FileUp, LockKeyhole, RefreshCw, Search } from "lucide-react";
import { type ReactElement, useMemo, useState } from "react";

import { UserBulaCard } from "@/components/bulas/user-bula-card";
import { UserBulaUploadDialog } from "@/components/bulas/user-bula-upload-dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useUserBulas } from "@/hooks/use-user-bulas";

function UserBulasLoadingState(): ReactElement {
  return (
    <div role="status" aria-label="Carregando suas bulas" className="grid gap-4 md:grid-cols-2">
      <span className="sr-only">Carregando suas bulas...</span>
      {Array.from({ length: 2 }, (_, index) => (
        <Card key={index} className="gap-4 py-5">
          <div className="flex items-center gap-3 px-5">
            <Skeleton className="h-10 w-10 rounded-lg" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-3 w-1/3" />
            </div>
          </div>
          <div className="flex justify-between px-5">
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-5 w-24" />
          </div>
        </Card>
      ))}
    </div>
  );
}

export function UserBulaSection(): ReactElement {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [requestedPage, setRequestedPage] = useState(1);
  const userBulasQuery = useUserBulas();
  const privateBulas = useMemo(
    () =>
      [...(userBulasQuery.data ?? [])]
        .filter((bula) => bula.corpus === "private")
        .sort(
          (firstBula, secondBula) =>
            new Date(secondBula.created_at).getTime() - new Date(firstBula.created_at).getTime()
        ),
    [userBulasQuery.data]
  );
  const normalize = (value: string): string =>
    value
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("pt-BR");
  const query = normalize(searchTerm.trim());
  const filteredBulas = privateBulas.filter((bula) => {
    const statusMatches =
      statusFilter === "all" ||
      (statusFilter === "processing" &&
        (bula.status === "pending" || bula.status === "processing")) ||
      (statusFilter === "error" && (bula.status === "error" || bula.status === "failed")) ||
      (statusFilter === "ready" && bula.status === "ready");
    return (
      statusMatches &&
      normalize([bula.alias, bula.drug_name, bula.manufacturer].filter(Boolean).join(" ")).includes(
        query
      )
    );
  });
  const pageCount = Math.max(1, Math.ceil(filteredBulas.length / 12));
  const page = Math.min(requestedPage, pageCount);
  const pageItems = filteredBulas.slice((page - 1) * 12, page * 12);

  return (
    <section id="minhas-bulas" aria-labelledby="user-bulas-title" className="space-y-5">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div className="space-y-1">
          <h1 id="user-bulas-title" className="text-2xl font-semibold tracking-tight">
            Minhas bulas
          </h1>
          <p className="text-muted-foreground text-sm">
            Organize seus documentos e retome a consulta de cada bula.
          </p>
        </div>
        <UserBulaUploadDialog />
      </div>

      <p className="text-muted-foreground flex items-start gap-2 text-sm">
        <LockKeyhole aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
        Seus uploads são privados. Eles não entram no catálogo nem no chat geral.
      </p>

      {userBulasQuery.isSuccess && privateBulas.length > 0 ? (
        <>
          <div className="grid grid-cols-3 gap-3" aria-label="Resumo das minhas bulas">
            {[
              {
                label: "Prontas",
                count: privateBulas.filter((bula) => bula.status === "ready").length,
              },
              {
                label: "Processando",
                count: privateBulas.filter(
                  (bula) => bula.status === "pending" || bula.status === "processing"
                ).length,
              },
              {
                label: "Com falha",
                count: privateBulas.filter(
                  (bula) => bula.status === "error" || bula.status === "failed"
                ).length,
              },
            ].map(({ label, count }) => (
              <div key={label} className="bg-card rounded-xl border px-4 py-3">
                <p className="text-muted-foreground text-xs">{label}</p>
                <p className="mt-1 text-xl font-semibold">{count}</p>
              </div>
            ))}
          </div>
          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_12rem]">
            <div className="relative">
              <Search
                aria-hidden="true"
                className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2"
              />
              <Input
                type="search"
                value={searchTerm}
                onChange={(event) => {
                  setSearchTerm(event.target.value);
                  setRequestedPage(1);
                }}
                aria-label="Buscar nas minhas bulas"
                placeholder="Buscar por nome, apelido ou fabricante"
                className="pl-9"
              />
            </div>
            <label className="sr-only" htmlFor="private-status">
              Filtrar minhas bulas por estado
            </label>
            <select
              id="private-status"
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value);
                setRequestedPage(1);
              }}
              className="border-input bg-background h-9 rounded-md border px-3 text-sm"
            >
              <option value="all">Todos os estados</option>
              <option value="ready">Prontas</option>
              <option value="processing">Processando</option>
              <option value="error">Com falha</option>
            </select>
          </div>
          <p className="text-muted-foreground text-sm" role="status">
            {filteredBulas.length} de {privateBulas.length} documentos
          </p>
        </>
      ) : null}

      {userBulasQuery.isLoading ? <UserBulasLoadingState /> : null}

      {userBulasQuery.isError ? (
        <Alert variant="destructive">
          <AlertCircle aria-hidden="true" />
          <AlertTitle>Não foi possível carregar suas bulas</AlertTitle>
          <AlertDescription className="flex flex-col items-start gap-3">
            <span>Verifique a conexão com o servidor e tente novamente.</span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => void userBulasQuery.refetch()}
            >
              <RefreshCw aria-hidden="true" className="h-3.5 w-3.5" />
              Tentar novamente
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}

      {userBulasQuery.isSuccess && privateBulas.length === 0 ? (
        <Card className="border-dashed shadow-none">
          <CardContent className="flex flex-col items-center py-10 text-center">
            <div className="bg-muted mb-3 flex h-12 w-12 items-center justify-center rounded-full">
              <FileUp aria-hidden="true" className="text-muted-foreground h-6 w-6" />
            </div>
            <h3 className="font-medium">Nenhuma bula enviada</h3>
            <p className="text-muted-foreground mt-1 max-w-md text-sm">
              Envie um PDF para acompanhar o processamento sem precisar atualizar a página.
            </p>
          </CardContent>
        </Card>
      ) : null}

      {userBulasQuery.isSuccess && filteredBulas.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {pageItems.map((bula) => (
            <UserBulaCard key={bula.id} bula={bula} />
          ))}
        </div>
      ) : null}
      {userBulasQuery.isSuccess && privateBulas.length > 0 && filteredBulas.length === 0 ? (
        <div className="rounded-xl border border-dashed p-8 text-center">
          <p>Nenhuma bula corresponde à busca.</p>
          <Button
            variant="outline"
            className="mt-3"
            onClick={() => {
              setSearchTerm("");
              setStatusFilter("all");
              setRequestedPage(1);
            }}
          >
            Limpar filtros
          </Button>
        </div>
      ) : null}
      {pageCount > 1 ? (
        <nav
          aria-label="Paginação das minhas bulas"
          className="flex items-center justify-between gap-3"
        >
          <span className="text-muted-foreground text-sm">
            Página {page} de {pageCount}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              disabled={page === 1}
              onClick={() => setRequestedPage(page - 1)}
            >
              Anterior
            </Button>
            <Button
              variant="outline"
              disabled={page === pageCount}
              onClick={() => setRequestedPage(page + 1)}
            >
              Próxima
            </Button>
          </div>
        </nav>
      ) : null}
    </section>
  );
}
