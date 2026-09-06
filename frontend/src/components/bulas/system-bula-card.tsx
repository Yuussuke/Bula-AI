import { ExternalLink, FileCheck2, MessageSquareText, ShieldCheck } from "lucide-react";
import type { ReactElement } from "react";
import { Link } from "react-router-dom";

import type { BulaStatus, SystemBulaPublicationState, SystemBulaResponse } from "@/api/bulas";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const ANVISA_ELECTRONIC_LEAFLET_URL = "https://consultas.anvisa.gov.br/#/bulario/";

function buildAnvisaElectronicLeafletUrl(registrationNumber: string): string {
  const normalizedRegistrationNumber = registrationNumber.trim();
  if (!normalizedRegistrationNumber) {
    return ANVISA_ELECTRONIC_LEAFLET_URL;
  }

  const searchParams = new URLSearchParams({ numeroRegistro: normalizedRegistrationNumber });
  return `${ANVISA_ELECTRONIC_LEAFLET_URL}q/?${searchParams.toString()}`;
}

interface SystemBulaCardProps {
  bula: SystemBulaResponse;
}

interface StatusPresentation {
  label: string;
  className: string;
}

const publicationPresentations: Record<SystemBulaPublicationState, StatusPresentation> = {
  staged: { label: "Em preparação", className: "border-amber-200 bg-amber-50 text-amber-800" },
  vetted: { label: "Revisada", className: "border-sky-200 bg-sky-50 text-sky-800" },
  published: { label: "Publicada", className: "border-emerald-200 bg-emerald-50 text-emerald-800" },
  withdrawn: { label: "Retirada", className: "border-slate-200 bg-slate-50 text-slate-700" },
  rejected: { label: "Rejeitada", className: "border-red-200 bg-red-50 text-red-800" },
};

const ingestionPresentations: Record<BulaStatus, StatusPresentation> = {
  pending: { label: "Pendente", className: "border-amber-200 bg-amber-50 text-amber-800" },
  processing: { label: "Processando", className: "border-amber-200 bg-amber-50 text-amber-800" },
  ready: { label: "Pronta", className: "border-emerald-200 bg-emerald-50 text-emerald-800" },
  failed: { label: "Falha", className: "border-red-200 bg-red-50 text-red-800" },
  error: { label: "Erro", className: "border-red-200 bg-red-50 text-red-800" },
};

const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "medium",
  timeZone: "America/Sao_Paulo",
});

function formatDate(dateValue: string | null): string {
  if (!dateValue) {
    return "Não informado";
  }

  const parsedDate = new Date(dateValue);
  if (Number.isNaN(parsedDate.getTime())) {
    return "Data inválida";
  }

  return dateFormatter.format(parsedDate);
}

export function SystemBulaCard({ bula }: SystemBulaCardProps): ReactElement {
  const publicationPresentation = publicationPresentations[bula.publication_state];
  const ingestionPresentation = ingestionPresentations[bula.ingestion_status];
  const canOpenChat = bula.publication_state === "published" && bula.ingestion_status === "ready";
  const anvisaElectronicLeafletUrl = buildAnvisaElectronicLeafletUrl(bula.registration_number);

  return (
    <Card className="gap-0 overflow-hidden py-0">
      <CardHeader className="gap-3 border-b py-5">
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline" className={cn("gap-1", publicationPresentation.className)}>
            <ShieldCheck aria-hidden="true" className="h-3.5 w-3.5" />
            {publicationPresentation.label}
          </Badge>
          <Badge variant="outline" className={cn("gap-1", ingestionPresentation.className)}>
            <FileCheck2 aria-hidden="true" className="h-3.5 w-3.5" />
            {ingestionPresentation.label}
          </Badge>
        </div>
        <div>
          <CardTitle className="text-lg leading-snug">{bula.product_name}</CardTitle>
          <p className="text-muted-foreground mt-1 text-sm">{bula.manufacturer}</p>
        </div>
      </CardHeader>

      <CardContent className="flex-1 space-y-4 py-5">
        <dl className="grid gap-3 text-sm">
          <div>
            <dt className="text-muted-foreground text-xs">Princípio ativo</dt>
            <dd className="font-medium">{bula.active_ingredient}</dd>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <dt className="text-muted-foreground text-xs">Concentração</dt>
              <dd>{bula.strength}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-xs">Público</dt>
              <dd>{bula.audience === "patient" ? "Paciente" : "Profissional"}</dd>
            </div>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">Forma farmacêutica</dt>
            <dd>{bula.pharmaceutical_form}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">Apresentação</dt>
            <dd>{bula.presentation}</dd>
          </div>
        </dl>

        <details className="border-border rounded-lg border px-3 py-2 text-sm">
          <summary className="cursor-pointer font-medium">Sobre esta bula</summary>
          <dl className="mt-3 grid gap-2 text-xs">
            <div>
              <dt className="text-muted-foreground">Registro ANVISA</dt>
              <dd className="break-all">{bula.registration_number}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Atualização no Bulário</dt>
              <dd>{formatDate(bula.source_updated_at ?? bula.source_published_at)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Tipo de documento</dt>
              <dd>{bula.audience === "patient" ? "Bula do paciente" : "Bula profissional"}</dd>
            </div>
          </dl>
          <a
            href={anvisaElectronicLeafletUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary mt-3 inline-flex items-center gap-1 text-xs hover:underline"
          >
            Consultar esta bula no Bulário Eletrônico da ANVISA
            <ExternalLink aria-hidden="true" className="h-3 w-3" />
          </a>
        </details>
      </CardContent>

      <CardFooter className="border-t py-4">
        {canOpenChat ? (
          <Button asChild className="w-full gap-2">
            <Link to={`/bulas/${bula.id}/chat`}>
              <MessageSquareText aria-hidden="true" className="h-4 w-4" />
              Conversar sobre esta bula
            </Link>
          </Button>
        ) : (
          <Button disabled className="w-full gap-2">
            <MessageSquareText aria-hidden="true" className="h-4 w-4" />
            Chat indisponível
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
