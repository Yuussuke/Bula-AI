import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ReactElement, useEffect, useState } from "react";

import { decideSharedBula, getSharedBula, getSharedPdf, type SharedDetail } from "@/api/curation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useIdempotencyKey } from "@/hooks/use-idempotency-key";
import { useAuthStore } from "@/store/auth";

const eventLabels: Record<string, string> = {
  submitted: "Submissão registrada",
  approved: "Aprovação",
  rejected: "Rejeição",
  withdrawn: "Retirada de consulta",
  ingestion_retry: "Nova tentativa de ingestão",
  ingestion_processing: "Processamento iniciado",
  ingestion_ready: "Processamento concluído",
  ingestion_failed: "Processamento falhou",
  ingestion_error: "Erro no processamento",
};

export function CurationDetail({
  id,
  canReview,
}: {
  id: string;
  canReview: boolean;
}): ReactElement {
  const detail = useQuery({
    queryKey: ["shared-bula", id],
    queryFn: () => getSharedBula(id),
    refetchInterval: (state) =>
      state.state.data?.document.review_status === "approved" &&
      ["pending", "processing"].includes(state.state.data.document.ingestion_status)
        ? 6000
        : false,
  });
  if (detail.isPending) return <p role="status">Carregando submissão…</p>;
  if (detail.isError)
    return (
      <p role="alert">
        Não foi possível carregar a submissão.{" "}
        <Button variant="link" onClick={() => void detail.refetch()}>
          Tentar novamente
        </Button>
      </p>
    );
  return (
    <CurationDocumentDetail
      key={`${id}-${detail.data.document.version}`}
      id={id}
      canReview={canReview}
      detail={detail.data}
    />
  );
}

function CurationDocumentDetail({
  id,
  canReview,
  detail,
}: {
  id: string;
  canReview: boolean;
  detail: SharedDetail;
}): ReactElement {
  const cache = useQueryClient();
  const operation = useIdempotencyKey();
  const reviewerId = useAuthStore((state) => state.user?.id);
  const [pdf, setPdf] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [productName, setProductName] = useState(detail.document.product_name);
  const [manufacturer, setManufacturer] = useState(detail.document.manufacturer ?? "");
  const [presentation, setPresentation] = useState(detail.document.presentation ?? "");
  const [strength, setStrength] = useState(detail.document.strength ?? "");
  const [hasChecked, setHasChecked] = useState(false);
  const [error, setError] = useState("");
  useEffect(
    () => () => {
      if (pdf) URL.revokeObjectURL(pdf);
    },
    [pdf]
  );
  const pdfRequest = useMutation({
    mutationFn: () => getSharedPdf(id),
    onSuccess: (blob) => setPdf(URL.createObjectURL(blob)),
    onError: (failure: Error) => setError(failure.message),
  });
  const decision = useMutation({
    mutationFn: (action: "approve" | "reject" | "withdraw" | "retry") => {
      const payload = {
        expected_version: detail.document.version,
        reason,
        product_name: action === "approve" ? productName.trim() : null,
        manufacturer: action === "approve" ? manufacturer.trim() || null : null,
        presentation: presentation.trim() || null,
        strength: strength.trim() || null,
      };
      return decideSharedBula(
        id,
        action,
        payload,
        operation.keyFor(JSON.stringify({ id, action, payload }))
      );
    },
    onSuccess: () => {
      setReason("");
      setHasChecked(false);
      operation.reset();
    },
    onError: (failure: Error) => setError(failure.message),
    onSettled: async () => {
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["shared-bulas"] }),
        cache.invalidateQueries({ queryKey: ["shared-bula", id] }),
      ]);
    },
  });
  const document = detail.document;
  const isSelfReview =
    document.review_status === "pending" && reviewerId === document.submitted_by_id;
  const pending = decision.isPending;
  const act = (action: "approve" | "reject" | "withdraw" | "retry"): void => {
    setError("");
    decision.mutate(action);
  };
  return (
    <section
      className="bg-muted/30 space-y-4 rounded-xl border p-4"
      aria-label="Conferência documental"
    >
      {detail.submitted_by_name && (
        <p className="text-sm">
          Enviado por: <strong>{detail.submitted_by_name}</strong>
        </p>
      )}
      {canReview && isSelfReview && (
        <p role="status" className="text-sm">
          Você enviou este documento. Outro Curador ou administrador deve realizar a revisão.
        </p>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="outline"
          disabled={pdfRequest.isPending}
          onClick={() => pdfRequest.mutate()}
        >
          Carregar PDF original
        </Button>
        {pdf && (
          <a
            className="text-primary underline"
            href={pdf}
            target="_blank"
            rel="noopener noreferrer"
          >
            Abrir PDF original
          </a>
        )}
        <span className="text-muted-foreground text-xs">
          Versão {document.version} · {document.content_size_bytes.toLocaleString("pt-BR")} bytes
        </span>
      </div>
      <details className="text-xs">
        <summary className="cursor-pointer">Integridade do arquivo</summary>
        <p className="mt-2 font-mono break-all">SHA-256: {document.sha256_checksum}</p>
      </details>
      {canReview && (
        <div className="space-y-3">
          <p className="text-muted-foreground text-sm">
            Conferência documental da fonte e do PDF. Esta decisão não certifica segurança clínica.
            Não revise uma submissão de sua autoria.
          </p>
          {document.review_status === "pending" && (
            <>
              <Label htmlFor={`product-${id}`}>Nome conferido no PDF</Label>
              <Input
                id={`product-${id}`}
                minLength={2}
                maxLength={255}
                value={productName}
                disabled={pending || isSelfReview}
                onChange={(event) => setProductName(event.target.value)}
              />
              <Label htmlFor={`manufacturer-${id}`}>Fabricante conferido (opcional)</Label>
              <Input
                id={`manufacturer-${id}`}
                maxLength={500}
                value={manufacturer}
                disabled={pending || isSelfReview}
                onChange={(event) => setManufacturer(event.target.value)}
              />
              <Label htmlFor={`presentation-${id}`}>Apresentação documentada (opcional)</Label>
              <Input
                id={`presentation-${id}`}
                maxLength={2000}
                value={presentation}
                disabled={pending}
                onChange={(event) => setPresentation(event.target.value)}
              />
              <Label htmlFor={`strength-${id}`}>Concentração documentada (opcional)</Label>
              <Input
                id={`strength-${id}`}
                maxLength={500}
                value={strength}
                disabled={pending}
                onChange={(event) => setStrength(event.target.value)}
              />
            </>
          )}
          {(document.review_status === "pending" || document.review_status === "approved") && (
            <>
              <Label htmlFor={`reason-${id}`}>Parecer ou justificativa</Label>
              <Textarea
                id={`reason-${id}`}
                value={reason}
                minLength={3}
                maxLength={3000}
                disabled={pending}
                onChange={(event) => setReason(event.target.value)}
              />
              {document.review_status === "pending" && (
                <label className="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={hasChecked}
                    disabled={pending}
                    onChange={(event) => setHasChecked(event.target.checked)}
                  />
                  Conferi o PDF original, a identificação da fonte e as condições relevantes.
                </label>
              )}
              <div className="flex flex-wrap gap-2">
                {document.review_status === "pending" ? (
                  <>
                    <Button
                      disabled={
                        pending ||
                        isSelfReview ||
                        productName.trim().length < 2 ||
                        !hasChecked ||
                        reason.trim().length < 3
                      }
                      onClick={() => act("approve")}
                    >
                      Aprovar e processar
                    </Button>
                    <Button
                      variant="destructive"
                      disabled={pending || isSelfReview || reason.trim().length < 3}
                      onClick={() => act("reject")}
                    >
                      Rejeitar
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      variant="destructive"
                      disabled={pending || reason.trim().length < 3}
                      onClick={() => act("withdraw")}
                    >
                      Retirar de consulta
                    </Button>
                    {(["failed", "error"].includes(document.ingestion_status) ||
                      (document.ingestion_status === "pending" &&
                        document.ingestion_job_id === null)) && (
                      <Button
                        disabled={pending || reason.trim().length < 3}
                        onClick={() => act("retry")}
                      >
                        Reenfileirar ingestão
                      </Button>
                    )}
                  </>
                )}
              </div>
            </>
          )}
        </div>
      )}
      {error && (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      )}
      {document.error_message && (
        <p className="text-destructive text-sm">{document.error_message}</p>
      )}
      {detail.events.length > 0 && (
        <details>
          <summary className="cursor-pointer text-sm font-medium">Histórico de decisões</summary>
          <ol className="mt-3 space-y-3 text-sm">
            {detail.events.map((event) => (
              <li key={event.id}>
                <p className="font-medium">
                  {eventLabels[event.action] ?? event.action} · {event.actor_name} · versão{" "}
                  {event.version}
                </p>
                <p>{event.reason}</p>
                <time className="text-muted-foreground text-xs">
                  {new Date(event.created_at).toLocaleString("pt-BR")}
                </time>
                <details className="mt-1 text-xs">
                  <summary className="cursor-pointer">Dados de auditoria</summary>
                  <p className="mt-2 break-all">Registro: {event.id}</p>
                  <p>
                    Perfil no momento da ação:{" "}
                    {event.actor_role ?? "Não registrado na versão anterior"}
                  </p>
                  <p className="break-all">
                    Operação: {event.operation_id ?? "Registro anterior ou transição técnica"}
                  </p>
                  {event.request_fingerprint && (
                    <p className="break-all">Hash da solicitação: {event.request_fingerprint}</p>
                  )}
                  {event.before_state || event.after_state ? (
                    <pre className="mt-2 max-h-64 overflow-auto break-all whitespace-pre-wrap">
                      {JSON.stringify(
                        { antes: event.before_state, depois: event.after_state },
                        null,
                        2
                      )}
                    </pre>
                  ) : (
                    <p>Este registro histórico não possui snapshots documentais.</p>
                  )}
                </details>
              </li>
            ))}
          </ol>
        </details>
      )}
    </section>
  );
}
