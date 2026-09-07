import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  FileText,
  Loader2,
  MessageSquareText,
} from "lucide-react";
import type { ReactElement } from "react";
import { Link } from "react-router-dom";

import type { BulaStatus, UserBulaResponse } from "@/api/bulas";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useBulaStatus } from "@/hooks/use-bula-status";

interface UserBulaCardProps {
  bula: UserBulaResponse;
}

interface BulaStatusBadgeProps {
  drugName: string;
  status: BulaStatus;
  errorMessage: string | null;
}

function BulaStatusBadge({ drugName, status, errorMessage }: BulaStatusBadgeProps): ReactElement {
  if (status === "pending" || status === "processing") {
    return (
      <Badge
        variant="outline"
        className="border-amber-200 bg-amber-50 text-amber-800"
        aria-label={`${drugName}: processando`}
      >
        <Loader2 aria-hidden="true" className="animate-spin" />
        Processando...
      </Badge>
    );
  }

  if (status === "ready") {
    return (
      <Badge
        variant="outline"
        className="border-emerald-200 bg-emerald-50 text-emerald-800"
        aria-label={`${drugName}: pronta`}
      >
        <CheckCircle2 aria-hidden="true" />
        Pronta
      </Badge>
    );
  }

  const visibleErrorMessage =
    errorMessage?.trim() || "Não foi possível concluir o processamento desta bula.";

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="rounded-full focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none"
          aria-label={`Ver erro de processamento de ${drugName}`}
        >
          <Badge variant="outline" className="cursor-help border-red-200 bg-red-50 text-red-800">
            <AlertCircle aria-hidden="true" />
            Erro
          </Badge>
        </button>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">
        <p>{visibleErrorMessage}</p>
      </TooltipContent>
    </Tooltip>
  );
}

function formatUploadDate(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(value));
}

export function UserBulaCard({ bula }: UserBulaCardProps): ReactElement {
  const statusQuery = useBulaStatus(bula);
  const currentStatus = statusQuery.data?.status ?? bula.status;
  const currentErrorMessage = statusQuery.data?.error_message ?? bula.error_message;
  const currentDrugName = statusQuery.data?.drug_name ?? bula.drug_name;
  const currentAlias = statusQuery.data?.alias ?? bula.alias;
  const currentManufacturer = statusQuery.data?.manufacturer ?? bula.manufacturer;
  const isMetadataPending = currentStatus === "pending" || currentStatus === "processing";
  const displayName = currentAlias || currentDrugName;
  const metadataDescription = currentAlias
    ? `${currentDrugName} · ${currentManufacturer || "Fabricante não identificado"}`
    : currentManufacturer || "Fabricante não identificado";

  return (
    <Card className="gap-4 py-5" aria-labelledby={`user-bula-${bula.id}-title`}>
      <CardHeader className="gap-4 px-5">
        <div className="flex min-w-0 items-start gap-3">
          <div className="bg-primary/10 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg">
            <FileText aria-hidden="true" className="text-primary h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <CardTitle id={`user-bula-${bula.id}-title`} className="truncate text-base">
              {currentAlias ? (
                currentAlias
              ) : isMetadataPending ? (
                <>
                  <span className="sr-only">Identificando medicamento</span>
                  <Skeleton className="h-5 w-4/5" />
                </>
              ) : (
                currentDrugName
              )}
            </CardTitle>
            {isMetadataPending ? (
              <Skeleton aria-label="Identificando fabricante" className="mt-2 h-4 w-1/2" />
            ) : (
              <p className="text-muted-foreground mt-1 truncate text-sm">{metadataDescription}</p>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex items-center justify-between gap-3 px-5">
        <p className="text-muted-foreground text-xs">
          Enviada em {formatUploadDate(bula.created_at)}
        </p>
        <div aria-live="polite">
          <BulaStatusBadge
            drugName={displayName}
            status={currentStatus}
            errorMessage={currentErrorMessage}
          />
        </div>
      </CardContent>

      {currentStatus === "ready" ? (
        <CardFooter className="border-border bg-muted/20 mt-auto border-t px-5 pt-4">
          <Button asChild size="lg" className="group w-full justify-between rounded-lg shadow-sm">
            <Link to={`/bulas/${bula.id}/chat`}>
              <span className="flex items-center gap-2">
                <MessageSquareText aria-hidden="true" className="h-4 w-4" />
                Conversar sobre esta bula
              </span>
              <ArrowRight
                aria-hidden="true"
                className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
              />
            </Link>
          </Button>
        </CardFooter>
      ) : null}
    </Card>
  );
}
