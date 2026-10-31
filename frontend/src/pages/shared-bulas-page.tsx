import { useQuery } from "@tanstack/react-query";
import { type FormEvent, type ReactElement, useState } from "react";
import { Link } from "react-router-dom";

import { type CurationView, listSharedBulas, type ReviewStatus } from "@/api/curation";
import { CurationDetail } from "@/components/bulas/curation-detail";
import { CurationSubmissionForm } from "@/components/bulas/curation-submission-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/store/auth";

const statuses: Record<ReviewStatus, string> = {
  pending: "Aguardando curadoria",
  approved: "Aprovada",
  rejected: "Rejeitada",
  withdrawn: "Retirada",
};

export function SharedBulasPage({ review = false }: { review?: boolean }): ReactElement {
  const role = useAuthStore((state) => state.user?.role);
  const canSubmit = role === "admin" || role === "contributor";
  const canReview = role === "admin" || role === "reviewer";
  const [mine, setMine] = useState(false);
  const view: CurationView = review ? "review" : mine ? "mine" : "public";
  const [status, setStatus] = useState<ReviewStatus | "">(review ? "pending" : "");
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [opened, setOpened] = useState<string | null>(null);
  const documents = useQuery({
    queryKey: ["shared-bulas", view, status, query, page],
    queryFn: () => listSharedBulas(view, status, query, page),
    enabled: !review || canReview,
    refetchInterval: (state) =>
      state.state.data?.items.some(
        (item) =>
          item.review_status === "approved" &&
          ["pending", "processing"].includes(item.ingestion_status)
      )
        ? 6000
        : false,
  });
  const search = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    setQuery(input.trim());
    setPage(1);
  };
  if (review && !canReview)
    return <p role="alert">Esta área é restrita aos Curadores e administradores.</p>;
  return (
    <section className="space-y-5" aria-labelledby="shared-title">
      <div>
        <h1 id="shared-title" className="text-2xl font-semibold">
          {review ? "Curadoria documental" : "Bulas compartilhadas"}
        </h1>
        <p className="text-muted-foreground mt-2 text-sm">
          {review
            ? "Confira o documento e sua origem antes de registrar o parecer."
            : "Documentos submetidos por Contribuidores, conferidos por Curadores e processados para consulta. As fontes podem ser diferentes da ANVISA."}
        </p>
      </div>
      {!review && canSubmit && <CurationSubmissionForm />}
      {!review && (
        <div className="flex flex-wrap gap-2">
          <Button
            variant={!mine ? "default" : "outline"}
            onClick={() => {
              setMine(false);
              setPage(1);
              setStatus("");
            }}
          >
            Disponíveis para consulta
          </Button>
          {canSubmit && (
            <Button
              variant={mine ? "default" : "outline"}
              onClick={() => {
                setMine(true);
                setPage(1);
                setStatus("");
              }}
            >
              Minhas submissões
            </Button>
          )}
          {canReview && (
            <Button asChild variant="outline">
              <Link to="/curadoria">Abrir fila de curadoria</Link>
            </Button>
          )}
        </div>
      )}
      <form onSubmit={search} className="flex flex-wrap gap-2">
        <Input
          aria-label="Buscar bula compartilhada"
          className="min-w-48 flex-1"
          placeholder="Buscar pelo nome"
          value={input}
          onChange={(event) => setInput(event.target.value)}
        />
        {view !== "public" && (
          <select
            aria-label="Situação da revisão"
            className="border-input bg-background rounded-md border px-3 text-sm"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value as ReviewStatus | "");
              setPage(1);
            }}
          >
            <option value="">Todas as situações</option>
            {Object.entries(statuses).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        )}
        <Button type="submit" variant="outline">
          Buscar
        </Button>
      </form>
      {documents.isPending ? (
        <p role="status">Carregando bulas…</p>
      ) : documents.isError ? (
        <p role="alert">
          Não foi possível carregar as bulas.{" "}
          <Button variant="link" onClick={() => void documents.refetch()}>
            Tentar novamente
          </Button>
        </p>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
            <span>{documents.data.total} documentos</span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                disabled={page === 1}
                onClick={() => setPage((value) => value - 1)}
              >
                Anterior
              </Button>
              <span>Página {page}</span>
              <Button
                variant="outline"
                disabled={page * 20 >= documents.data.total}
                onClick={() => setPage((value) => value + 1)}
              >
                Próxima
              </Button>
            </div>
          </div>
          {documents.data.items.length === 0 && (
            <p className="text-muted-foreground rounded-xl border p-6">
              Nenhum documento nesta situação.
            </p>
          )}
          <div className="space-y-3">
            {documents.data.items.map((document) => (
              <article key={document.id} className="bg-card space-y-3 rounded-xl border p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="font-semibold">{document.product_name}</h2>
                    <p className="text-muted-foreground text-sm">
                      {[document.manufacturer, document.presentation, document.strength]
                        .filter(Boolean)
                        .join(" · ") || "Identificação completa disponível após o processamento."}
                    </p>
                  </div>
                  <span className="text-muted-foreground text-xs">
                    {statuses[document.review_status]}
                    {document.review_status === "approved" && !document.is_available
                      ? ` · ${document.ingestion_status === "failed" || document.ingestion_status === "error" ? "Falha no processamento" : "Aguardando processamento"}`
                      : ""}
                  </span>
                </div>
                <p className="text-muted-foreground text-sm">
                  Fonte declarada: {document.source_description}
                </p>
                <div className="flex flex-wrap items-center gap-3">
                  <a
                    className="text-primary text-sm break-all underline"
                    href={document.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Consultar origem do documento
                  </a>
                  {document.is_available && (
                    <Button asChild variant="outline" size="sm">
                      <Link to={`/bulas/${document.id}/chat`}>Conversar sobre esta bula</Link>
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      setOpened((value) => (value === document.id ? null : document.id))
                    }
                    aria-expanded={opened === document.id}
                  >
                    {review ? "Conferir submissão" : "Ver documento e histórico"}
                  </Button>
                </div>
                {opened === document.id && (
                  <CurationDetail id={document.id} canReview={review && canReview} />
                )}
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
