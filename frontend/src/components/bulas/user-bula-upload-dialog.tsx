import { AlertCircle, Loader2, Upload } from "lucide-react";
import { type FormEvent, type ReactElement, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { useUploadBula } from "@/hooks/use-user-bulas";

export function UserBulaUploadDialog(): ReactElement {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const uploadMutation = useUploadBula();
  const canSubmit = selectedFile !== null;

  const resetForm = (): void => {
    setSelectedFile(null);
    uploadMutation.reset();
  };

  const handleOpenChange = (nextIsOpen: boolean): void => {
    if (uploadMutation.isPending) {
      return;
    }

    setIsOpen(nextIsOpen);
    if (!nextIsOpen) {
      resetForm();
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (!canSubmit || selectedFile === null || uploadMutation.isPending) {
      return;
    }

    uploadMutation.mutate(
      {
        file: selectedFile,
      },
      {
        onSuccess: () => {
          setIsOpen(false);
          resetForm();
        },
      }
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button type="button" className="gap-2">
          <Upload aria-hidden="true" className="h-4 w-4" />
          Enviar bula
        </Button>
      </DialogTrigger>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>Enviar uma bula</DialogTitle>
          <DialogDescription>
            Envie um PDF de até 10 MB. Identificaremos automaticamente o medicamento e o fabricante
            durante o processamento.
          </DialogDescription>
        </DialogHeader>

        <form className="space-y-5" onSubmit={handleSubmit} noValidate>
          <div className="space-y-2">
            <Label htmlFor="user-bula-file">Arquivo PDF</Label>
            <Input
              id="user-bula-file"
              type="file"
              accept="application/pdf,.pdf"
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              required
            />
          </div>

          {uploadMutation.isError ? (
            <Alert variant="destructive">
              <AlertCircle aria-hidden="true" />
              <AlertTitle>Não foi possível enviar a bula</AlertTitle>
              <AlertDescription>{uploadMutation.error.message}</AlertDescription>
            </Alert>
          ) : null}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={uploadMutation.isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={!canSubmit || uploadMutation.isPending}>
              {uploadMutation.isPending ? (
                <>
                  <Loader2 aria-hidden="true" className="animate-spin" />
                  Enviando...
                </>
              ) : (
                "Enviar PDF"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
