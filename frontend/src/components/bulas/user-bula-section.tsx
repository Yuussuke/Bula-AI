import { AlertCircle, FileUp, RefreshCw } from "lucide-react";
import { type ReactElement, useMemo } from "react";

import { UserBulaCard } from "@/components/bulas/user-bula-card";
import { UserBulaUploadDialog } from "@/components/bulas/user-bula-upload-dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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

  return (
    <section id="minhas-bulas" aria-labelledby="user-bulas-title" className="space-y-5">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div className="space-y-1">
          <h2 id="user-bulas-title" className="text-xl font-semibold">
            Minhas bulas
          </h2>
          <p className="text-muted-foreground text-sm">
            Acompanhe o processamento dos PDFs enviados por você.
          </p>
        </div>
        <UserBulaUploadDialog />
      </div>

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

      {userBulasQuery.isSuccess && privateBulas.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {privateBulas.map((bula) => (
            <UserBulaCard key={bula.id} bula={bula} />
          ))}
        </div>
      ) : null}
    </section>
  );
}
