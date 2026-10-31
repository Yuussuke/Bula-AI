import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MoreHorizontal, Pencil, Pin, PinOff, Trash2 } from "lucide-react";
import { type FormEvent, type ReactElement, useId, useRef, useState } from "react";

import {
  type ChatSessionResponse,
  deleteChatSession,
  renameChatSession,
  setChatSessionPinned,
} from "@/api/chat";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";

type ConversationMutation =
  | { kind: "rename"; title: string }
  | { kind: "delete" }
  | { kind: "pin"; isPinned: boolean };

interface ConversationActionsProps {
  session: ChatSessionResponse;
  isDisabled?: boolean;
  onDeleted: () => void;
}

export function ConversationActions({
  session,
  isDisabled = false,
  onDeleted,
}: ConversationActionsProps): ReactElement {
  const queryClient = useQueryClient();
  const [action, setAction] = useState<"rename" | "delete" | null>(null);
  const [title, setTitle] = useState(session.title);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const inputId = useId();
  const mutation = useMutation({
    mutationFn: async (request: ConversationMutation): Promise<void> => {
      if (request.kind === "rename") await renameChatSession(session.id, request.title);
      else if (request.kind === "pin") await setChatSessionPinned(session.id, request.isPinned);
      else await deleteChatSession(session.id);
    },
    retry: false,
    onSuccess: (_, request) => {
      setAction(null);
      if (request.kind === "delete") {
        onDeleted();
        queryClient.removeQueries({
          predicate: (query) =>
            query.queryKey[0] === "chat-session" && query.queryKey[2] === session.id,
        });
      }
      void queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });
  const openAction = (kind: "rename" | "delete"): void => {
    mutation.reset();
    setTitle(session.title);
    setAction(kind);
  };
  const restoreFocus = (event: Event): void => {
    event.preventDefault();
    triggerRef.current?.focus();
  };
  const saveTitle = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const cleanTitle = title.trim();
    if (!cleanTitle || mutation.isPending) return;
    mutation.mutate({ kind: "rename", title: cleanTitle });
  };
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            ref={triggerRef}
            variant="ghost"
            size="icon-sm"
            disabled={isDisabled || mutation.isPending}
            aria-label={`Opções da conversa ${session.title}`}
            className="text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground mt-1 mr-1 h-8 w-8 shrink-0"
          >
            <MoreHorizontal aria-hidden="true" className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem
            onSelect={() => {
              mutation.reset();
              mutation.mutate({ kind: "pin", isPinned: !session.is_pinned });
            }}
          >
            {session.is_pinned ? <PinOff aria-hidden="true" /> : <Pin aria-hidden="true" />}
            {session.is_pinned ? "Desafixar" : "Fixar"}
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => openAction("rename")}>
            <Pencil aria-hidden="true" />
            Renomear
          </DropdownMenuItem>
          <DropdownMenuItem variant="destructive" onSelect={() => openAction("delete")}>
            <Trash2 aria-hidden="true" />
            Excluir
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      {mutation.isError && action === null ? (
        <p role="alert" className="text-destructive basis-full px-3 pb-2 text-xs">
          Não foi possível alterar a fixação. Tente novamente pelo menu.
        </p>
      ) : null}
      <Dialog
        open={action === "rename"}
        onOpenChange={(open) => {
          if (!open && !mutation.isPending) setAction(null);
        }}
      >
        <DialogContent showCloseButton={false} onCloseAutoFocus={restoreFocus}>
          <DialogHeader>
            <DialogTitle>Renomear conversa</DialogTitle>
            <DialogDescription>Escolha um nome com até 50 caracteres.</DialogDescription>
          </DialogHeader>
          <form onSubmit={saveTitle} className="space-y-4">
            <label htmlFor={inputId} className="sr-only">
              Nome da conversa
            </label>
            <Input
              id={inputId}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              maxLength={50}
              disabled={mutation.isPending}
              required
            />
            {mutation.isError ? (
              <p role="alert" className="text-destructive text-sm">
                Não foi possível salvar o nome. Tente novamente.
              </p>
            ) : null}
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                disabled={mutation.isPending}
                onClick={() => setAction(null)}
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={mutation.isPending || !title.trim()}>
                {mutation.isPending ? "Salvando…" : "Salvar"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      <AlertDialog
        open={action === "delete"}
        onOpenChange={(open) => {
          if (!open && !mutation.isPending) setAction(null);
        }}
      >
        <AlertDialogContent onCloseAutoFocus={restoreFocus}>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir conversa?</AlertDialogTitle>
            <AlertDialogDescription>
              A conversa “{session.title}” e suas mensagens serão excluídas. Esta ação não pode ser
              desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {mutation.isError ? (
            <p role="alert" className="text-destructive text-sm">
              Não foi possível excluir a conversa. Tente novamente.
            </p>
          ) : null}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={mutation.isPending}>Cancelar</AlertDialogCancel>
            <Button
              variant="destructive"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate({ kind: "delete" })}
            >
              {mutation.isPending ? "Excluindo…" : "Excluir conversa"}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
