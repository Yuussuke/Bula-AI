import { Pencil } from "lucide-react";
import { type FormEvent, type ReactElement, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useUpdateBulaAlias } from "@/hooks/use-user-bulas";

export function BulaAliasDialog({
  bulaId,
  alias,
  drugName,
}: {
  bulaId: string;
  alias: string | null;
  drugName: string;
}): ReactElement {
  const [isOpen, setIsOpen] = useState(false);
  const [draft, setDraft] = useState(alias ?? "");
  const updateAlias = useUpdateBulaAlias(bulaId);

  const handleOpenChange = (nextOpen: boolean): void => {
    if (updateAlias.isPending) return;
    if (nextOpen) {
      setDraft(alias ?? "");
      updateAlias.reset();
    }
    setIsOpen(nextOpen);
  };
  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (updateAlias.isPending) return;
    updateAlias.mutate(draft, { onSuccess: () => setIsOpen(false) });
  };
  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={`Editar apelido de ${alias || drugName}`}
        >
          <Pencil aria-hidden="true" className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Editar apelido</DialogTitle>
          <DialogDescription>
            O nome oficial {drugName} permanece igual. O apelido é visível apenas para você.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Label htmlFor={`alias-${bulaId}`}>Apelido da bula</Label>
          <Input
            id={`alias-${bulaId}`}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            maxLength={100}
            disabled={updateAlias.isPending}
          />
          <p className="text-muted-foreground text-xs">
            Deixe em branco para voltar a exibir o nome oficial.
          </p>
          {updateAlias.isError ? (
            <p role="alert" className="text-destructive text-sm">
              Não foi possível salvar o apelido. Tente novamente.
            </p>
          ) : null}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsOpen(false)}
              disabled={updateAlias.isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={updateAlias.isPending}>
              {updateAlias.isPending ? "Salvando…" : "Salvar apelido"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
