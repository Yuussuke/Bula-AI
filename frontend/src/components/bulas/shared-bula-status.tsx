import { AlertCircle, CheckCircle2, Clock3, Loader2 } from "lucide-react";
import type { ReactElement } from "react";

import type { ReviewStatus, SharedBula } from "@/api/curation";
import { Badge } from "@/components/ui/badge";

const reviewLabels: Record<ReviewStatus, string> = {
  pending: "Aguardando curadoria",
  approved: "Aprovada",
  rejected: "Rejeitada",
  withdrawn: "Retirada",
};

export function SharedBulaStatus({ document }: { document: SharedBula }): ReactElement {
  const hasFailed = document.ingestion_status === "failed" || document.ingestion_status === "error";
  return (
    <div className="flex flex-wrap items-center gap-2" aria-label="Situação da bula">
      <Badge variant="outline">{reviewLabels[document.review_status]}</Badge>
      {document.review_status === "approved" ? (
        <Badge variant={hasFailed ? "destructive" : "secondary"}>
          {document.ingestion_status === "processing" ? (
            <>
              <Loader2 aria-hidden="true" className="motion-safe:animate-spin" />
              Processando
            </>
          ) : document.ingestion_status === "pending" ? (
            <>
              <Clock3 aria-hidden="true" />
              Aguardando processamento
            </>
          ) : hasFailed ? (
            <>
              <AlertCircle aria-hidden="true" />
              Falha no processamento
            </>
          ) : document.is_available ? (
            <>
              <CheckCircle2 aria-hidden="true" />
              Disponível para consulta
            </>
          ) : (
            "Indisponível para consulta"
          )}
        </Badge>
      ) : null}
    </div>
  );
}
