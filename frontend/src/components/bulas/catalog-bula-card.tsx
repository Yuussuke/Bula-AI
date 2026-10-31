import { ChevronDown, ExternalLink, MessageSquareText } from "lucide-react";
import type { ReactElement } from "react";
import { Link, useLocation } from "react-router-dom";

import type { PublicCatalogBulaResponse } from "@/api/bulas";
import { Button } from "@/components/ui/button";

interface CatalogBulaCardProps {
  bula: PublicCatalogBulaResponse;
}

function formatDate(value: string | null): string {
  if (!value) return "Não informado";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "medium",
    timeZone: "America/Sao_Paulo",
  }).format(new Date(value));
}

export function CatalogBulaCard({ bula }: CatalogBulaCardProps): ReactElement {
  const location = useLocation();
  const canOpenChat = bula.is_available;
  return (
    <article className="bg-card space-y-3 px-4 py-4 sm:px-5" aria-labelledby={`catalog-${bula.id}`}>
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div className="min-w-0 space-y-1">
          <h2 id={`catalog-${bula.id}`} className="font-semibold">
            {bula.product_name}
            <span className="text-muted-foreground ml-2 rounded border px-1.5 py-0.5 text-xs font-normal">
              {bula.corpus === "system" ? "ANVISA" : "Compartilhada"}
            </span>
          </h2>
          <p className="text-muted-foreground line-clamp-2 text-sm">
            {[bula.strength, bula.pharmaceutical_form].filter(Boolean).join(" · ") ||
              "Apresentação não informada"}
          </p>
          <p className="text-muted-foreground text-xs">
            {bula.manufacturer ?? "Fabricante não informado"}
          </p>
        </div>
        {canOpenChat ? (
          <Button asChild variant="outline" size="sm" className="shrink-0 self-start">
            <Link
              to={`/bulas/${bula.id}/chat`}
              state={{ returnTo: `${location.pathname}${location.search}` }}
              aria-label={`Conversar sobre ${bula.product_name}, ${bula.strength}`}
            >
              <MessageSquareText aria-hidden="true" className="mr-2 h-4 w-4" />
              Conversar
            </Link>
          </Button>
        ) : (
          <Button disabled variant="outline" size="sm">
            Chat indisponível
          </Button>
        )}
      </div>
      <details className="group text-sm">
        <summary className="text-primary flex w-fit cursor-pointer list-none items-center gap-1 rounded-sm text-xs focus-visible:outline-2">
          <ChevronDown
            aria-hidden="true"
            className="h-3.5 w-3.5 transition-transform group-open:rotate-180"
          />
          Detalhes e fonte
        </summary>
        <div className="bg-muted/30 mt-3 grid gap-3 rounded-lg p-4 sm:grid-cols-2">
          <div>
            <p className="text-muted-foreground text-xs">Princípio ativo</p>
            <p>{bula.active_ingredient ?? "Não informado"}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Apresentação</p>
            <p>{bula.presentation ?? "Não informada"}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Concentração e forma</p>
            <p>
              {[bula.strength, bula.pharmaceutical_form].filter(Boolean).join(" · ") ||
                "Não informadas"}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Registro ANVISA</p>
            <p>{bula.registration_number ?? "Não informado"}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Atualização da fonte</p>
            <p>{formatDate(bula.source_updated_at ?? bula.source_published_at)}</p>
          </div>
          <p className="text-muted-foreground text-xs">
            {bula.audience === "patient"
              ? "Bula do paciente"
              : bula.audience === "professional"
                ? "Bula profissional"
                : "Público não informado"}
          </p>
          <a
            href={bula.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary inline-flex items-center gap-1 text-xs underline underline-offset-4"
          >
            {bula.corpus === "system" ? "Consultar fonte na ANVISA" : "Consultar fonte original"}
            <ExternalLink aria-hidden="true" className="h-3 w-3" />
          </a>
        </div>
      </details>
    </article>
  );
}
