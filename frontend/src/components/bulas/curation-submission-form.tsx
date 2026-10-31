import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, type ReactElement, useRef, useState } from "react";

import { type SharedSubmissionInput, submitSharedBula } from "@/api/curation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useIdempotencyKey } from "@/hooks/use-idempotency-key";

export function CurationSubmissionForm(): ReactElement {
  const cache = useQueryClient();
  const form = useRef<HTMLFormElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const operation = useIdempotencyKey();
  const mutation = useMutation({
    mutationFn: (input: SharedSubmissionInput) =>
      submitSharedBula(
        input,
        operation.keyFor(
          JSON.stringify({
            ...input,
            file: {
              name: input.file.name,
              size: input.file.size,
              lastModified: input.file.lastModified,
            },
          })
        )
      ),
    onSuccess: () => {
      form.current?.reset();
      setSubmitted(true);
      operation.reset();
      void cache.invalidateQueries({ queryKey: ["shared-bulas"] });
    },
    onError: (failure: Error) => setError(failure.message),
  });
  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    setError("");
    setSubmitted(false);
    const values = new FormData(event.currentTarget);
    const file = fileInput.current?.files?.[0];
    if (!file || file.size === 0 || file.size > 10 * 1024 * 1024) {
      setError("Selecione um PDF de até 10 MB.");
      return;
    }
    const sourceUrl = values.get("source_url");
    const sourceDescription = values.get("source_description");
    const productName = values.get("product_name");
    const manufacturer = values.get("manufacturer");
    if (
      typeof sourceUrl !== "string" ||
      typeof sourceDescription !== "string" ||
      typeof productName !== "string" ||
      typeof manufacturer !== "string"
    ) {
      setError("Identifique a fonte e o endereço do documento.");
      return;
    }
    mutation.mutate({
      file,
      source_url: sourceUrl,
      source_description: sourceDescription,
      product_name: productName,
      manufacturer: manufacturer.trim() || null,
    });
  };
  return (
    <details className="bg-card rounded-xl border p-4">
      <summary className="text-primary cursor-pointer font-medium">
        Submeter uma bula para curadoria
      </summary>
      <form
        ref={form}
        onSubmit={handleSubmit}
        className="mt-4 grid gap-4"
        aria-label="Submissão de bula compartilhada"
      >
        <p className="text-muted-foreground text-sm">
          O arquivo aguarda conferência do Curador. Só ficará disponível após aprovação e
          processamento, sem alterar suas bulas privadas.
        </p>
        <div>
          <Label htmlFor="shared-product">Nome do medicamento no PDF</Label>
          <Input
            id="shared-product"
            name="product_name"
            minLength={2}
            maxLength={255}
            required
            disabled={mutation.isPending}
          />
        </div>
        <div>
          <Label htmlFor="shared-manufacturer">Fabricante identificado (opcional)</Label>
          <Input
            id="shared-manufacturer"
            name="manufacturer"
            maxLength={500}
            disabled={mutation.isPending}
          />
        </div>
        <div>
          <Label htmlFor="shared-file">PDF original (até 10 MB)</Label>
          <Input
            id="shared-file"
            ref={fileInput}
            onChange={() => operation.reset()}
            name="file"
            type="file"
            accept="application/pdf"
            required
            disabled={mutation.isPending}
          />
        </div>
        <div>
          <Label htmlFor="shared-source">Endereço da fonte</Label>
          <Input
            id="shared-source"
            name="source_url"
            type="url"
            placeholder="https://..."
            maxLength={2048}
            required
            disabled={mutation.isPending}
          />
        </div>
        <div>
          <Label htmlFor="shared-description">Identificação e origem do documento</Label>
          <Textarea
            id="shared-description"
            name="source_description"
            placeholder="Identifique o responsável pela fonte e a versão do documento, quando disponíveis."
            minLength={3}
            maxLength={1000}
            required
            disabled={mutation.isPending}
          />
        </div>
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
        {submitted && (
          <p role="status" className="text-primary text-sm">
            Submissão recebida. Acompanhe em Minhas submissões.
          </p>
        )}
        <Button type="submit" disabled={mutation.isPending} className="w-fit">
          {mutation.isPending ? "Enviando…" : "Enviar para curadoria"}
        </Button>
      </form>
    </details>
  );
}
