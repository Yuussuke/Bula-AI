import { AlertCircle, CheckCircle2, FileText, Loader2 } from "lucide-react";
import type { ReactElement } from "react";

import type { BulaStatus, UserBulaResponse } from "@/api/bulas";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

  return (
    <Card className="gap-4 py-5" aria-labelledby={`user-bula-${bula.id}-title`}>
      <CardHeader className="gap-4 px-5">
        <div className="flex min-w-0 items-start gap-3">
          <div className="bg-primary/10 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg">
            <FileText aria-hidden="true" className="text-primary h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <CardTitle id={`user-bula-${bula.id}-title`} className="truncate text-base">
              {bula.drug_name}
            </CardTitle>
            <p className="text-muted-foreground mt-1 truncate text-sm">
              {bula.manufacturer || "Fabricante não informado"}
            </p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex items-center justify-between gap-3 px-5">
        <p className="text-muted-foreground text-xs">
          Enviada em {formatUploadDate(bula.created_at)}
        </p>
        <div aria-live="polite">
          <BulaStatusBadge
            drugName={bula.drug_name}
            status={currentStatus}
            errorMessage={currentErrorMessage}
          />
        </div>
      </CardContent>
    </Card>
  );
}
