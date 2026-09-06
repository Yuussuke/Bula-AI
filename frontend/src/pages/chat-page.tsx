import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ArrowLeft, FileText, History } from "lucide-react";
import { type ReactElement, useState } from "react";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";

import { getSystemBula } from "@/api/bulas";
import { ChatComposer } from "@/components/chat/chat-composer";
import { ChatMessageList } from "@/components/chat/chat-message-list";
import { ChatSessionNavigation } from "@/components/chat/chat-session-navigation";
import { ModeIndicator } from "@/components/chat/mode-indicator";
import { MedicalWarning } from "@/components/medical-warning";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useChatSession } from "@/hooks/use-chat-session";
import { ApiError } from "@/lib/api";

function isNotFoundError(error: Error | null): boolean {
  return error instanceof ApiError && error.status === 404;
}

function ChatPageLoadingState(): ReactElement {
  return (
    <div role="status" aria-label="Carregando conversa" className="bg-muted/20 flex min-h-screen">
      <span className="sr-only">Carregando conversa…</span>

      <aside className="bg-sidebar border-sidebar-border hidden w-72 shrink-0 border-r lg:block">
        <div className="border-sidebar-border flex items-center gap-3 border-b p-5">
          <Skeleton className="bg-sidebar-accent h-9 w-9 shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="bg-sidebar-accent h-4 w-20" />
            <Skeleton className="bg-sidebar-accent h-3 w-36" />
          </div>
        </div>
        <div className="border-sidebar-border space-y-3 border-b p-4">
          <Skeleton className="bg-sidebar-accent h-9 w-full" />
          <Skeleton className="bg-sidebar-accent h-9 w-full" />
        </div>
        <div className="space-y-3 p-4">
          <Skeleton className="bg-sidebar-accent h-3 w-36" />
          <Skeleton className="bg-sidebar-accent h-14 w-full" />
          <Skeleton className="bg-sidebar-accent h-14 w-full" />
          <Skeleton className="bg-sidebar-accent h-14 w-full" />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="bg-card border-border border-b">
          <div className="mx-auto flex max-w-5xl items-center gap-3 px-3 py-3 sm:px-6 sm:py-4">
            <Skeleton className="h-9 w-9 lg:hidden" />
            <div className="min-w-0 flex-1 space-y-2">
              <Skeleton className="h-5 w-full max-w-sm" />
              <Skeleton className="h-4 w-full max-w-lg" />
            </div>
            <Skeleton className="h-7 w-32" />
          </div>
        </header>

        <main className="mx-auto flex w-full max-w-5xl flex-1 p-3 sm:p-6">
          <Card className="flex min-h-[75vh] w-full flex-col gap-0 overflow-hidden py-0">
            <div className="border-border border-b p-4">
              <Skeleton className="h-16 w-full" />
            </div>
            <div className="flex-1 space-y-6 p-4 sm:p-5">
              <div className="flex gap-3">
                <Skeleton className="h-8 w-8 shrink-0 rounded-full" />
                <div className="w-full max-w-lg space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-20 w-full" />
                </div>
              </div>
              <div className="ml-auto w-full max-w-md space-y-2">
                <Skeleton className="ml-auto h-4 w-20" />
                <Skeleton className="h-14 w-full" />
              </div>
            </div>
            <div className="border-border flex gap-3 border-t p-4">
              <Skeleton className="h-11 flex-1" />
              <Skeleton className="h-11 w-11" />
            </div>
          </Card>
        </main>
      </div>
    </div>
  );
}

function ChatPageUnavailable({ message }: { message: string }): ReactElement {
  return (
    <main className="bg-background flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-lg p-6 text-center">
        <AlertCircle aria-hidden="true" className="text-destructive mx-auto h-10 w-10" />
        <h1 className="mt-4 text-xl font-semibold">Chat indisponível</h1>
        <p className="text-muted-foreground mt-2 text-sm">{message}</p>
        <Button asChild className="mt-5">
          <Link to="/">Voltar para as bulas</Link>
        </Button>
      </Card>
    </main>
  );
}

export function ChatPage(): ReactElement {
  const { bulaId } = useParams<{ bulaId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [question, setQuestion] = useState("");
  const [isMobileSessionsOpen, setIsMobileSessionsOpen] = useState(false);
  const sessionId = searchParams.get("session");
  const resolvedBulaId = bulaId ?? "";

  const bulaQuery = useQuery({
    queryKey: ["system-bula", resolvedBulaId],
    queryFn: () => getSystemBula(resolvedBulaId),
    enabled: Boolean(bulaId),
    staleTime: 5 * 60 * 1000,
  });
  const chatSession = useChatSession({
    bulaId: resolvedBulaId,
    sessionId,
    onSessionCreated: (createdSessionId) => {
      setSearchParams({ session: createdSessionId }, { replace: true });
    },
  });

  const handleSendQuestion = (): void => {
    const cleanQuestion = question.trim();
    if (!cleanQuestion) {
      return;
    }

    setQuestion("");
    void chatSession.sendQuestion(cleanQuestion).then((wasSent) => {
      if (!wasSent) {
        setQuestion((currentQuestion) => currentQuestion || cleanQuestion);
      }
    });
  };

  const handleStartNewSession = (): void => {
    setSearchParams({}, { replace: true });
  };

  if (!bulaId) {
    return <Navigate to="/" replace />;
  }

  if (bulaQuery.isLoading || chatSession.isLoading) {
    return <ChatPageLoadingState />;
  }

  if (isNotFoundError(bulaQuery.error) || isNotFoundError(chatSession.loadError)) {
    return (
      <ChatPageUnavailable message="A bula ou a conversa não existe, não está publicada ou não pertence a este usuário." />
    );
  }

  if (bulaQuery.error || chatSession.loadError || !bulaQuery.data) {
    return (
      <ChatPageUnavailable message="Não foi possível carregar a conversa. Verifique a conexão e tente novamente." />
    );
  }

  if (sessionId && chatSession.loadedBulaId !== bulaId) {
    return (
      <ChatPageUnavailable message="Esta conversa pertence a outra bula e não pode ser aberta nesta página." />
    );
  }

  return (
    <div className="bg-muted/20 flex min-h-screen">
      <aside className="bg-sidebar text-sidebar-foreground border-sidebar-border hidden w-72 shrink-0 border-r lg:block">
        <ChatSessionNavigation
          bulaId={bulaId}
          currentSessionId={sessionId}
          onStartNewSession={handleStartNewSession}
        />
      </aside>

      <Sheet open={isMobileSessionsOpen} onOpenChange={setIsMobileSessionsOpen}>
        <SheetContent
          side="left"
          className="bg-sidebar text-sidebar-foreground w-[85%] max-w-80 gap-0 p-0"
        >
          <SheetHeader className="sr-only">
            <SheetTitle>Conversas desta bula</SheetTitle>
          </SheetHeader>
          <ChatSessionNavigation
            bulaId={bulaId}
            currentSessionId={sessionId}
            onStartNewSession={handleStartNewSession}
            onNavigate={() => setIsMobileSessionsOpen(false)}
          />
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="bg-card border-border border-b">
          <div className="mx-auto flex max-w-5xl items-center gap-2 px-3 py-3 sm:gap-3 sm:px-6 sm:py-4">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label="Abrir conversas"
              className="lg:hidden"
              onClick={() => setIsMobileSessionsOpen(true)}
            >
              <History aria-hidden="true" className="h-5 w-5" />
            </Button>
            <Button
              asChild
              variant="ghost"
              size="icon"
              aria-label="Voltar para as bulas"
              className="lg:hidden"
            >
              <Link to="/">
                <ArrowLeft aria-hidden="true" className="h-5 w-5" />
              </Link>
            </Button>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <FileText aria-hidden="true" className="text-primary h-4 w-4 shrink-0" />
                <h1 className="truncate text-base font-semibold sm:text-lg">
                  {bulaQuery.data.product_name}
                </h1>
              </div>
              <p className="text-muted-foreground truncate text-xs sm:text-sm">
                {bulaQuery.data.active_ingredient} · {bulaQuery.data.strength} ·{" "}
                {bulaQuery.data.manufacturer}
              </p>
            </div>
            <ModeIndicator />
          </div>
        </header>

        <main className="mx-auto flex w-full max-w-5xl flex-1 p-3 sm:p-6">
          <Card className="flex min-h-[75vh] w-full flex-col overflow-hidden py-0">
            <MedicalWarning />
            {sessionId && chatSession.messages.length === 0 ? (
              <Alert className="m-4 w-auto">
                <AlertCircle aria-hidden="true" />
                <AlertTitle>Conversa sem mensagens</AlertTitle>
                <AlertDescription>
                  Esta sessão ainda não possui mensagens. Envie uma pergunta para começar.
                </AlertDescription>
              </Alert>
            ) : null}
            <ChatMessageList messages={chatSession.messages} isResponding={chatSession.isSending} />
            {chatSession.sendError ? (
              <Alert variant="destructive" className="mx-4 mb-3 w-auto sm:mx-5">
                <AlertCircle aria-hidden="true" />
                <AlertTitle>
                  {isNotFoundError(chatSession.sendError)
                    ? "Conversa indisponível"
                    : "Não foi possível enviar"}
                </AlertTitle>
                <AlertDescription>
                  {isNotFoundError(chatSession.sendError)
                    ? "A conversa ou a bula pode ter sido retirada. Sua pergunta foi preservada."
                    : "Sua pergunta foi preservada. Tente novamente em alguns instantes."}
                </AlertDescription>
              </Alert>
            ) : null}
            <ChatComposer
              value={question}
              isDisabled={chatSession.isSending}
              onChange={setQuestion}
              onSubmit={handleSendQuestion}
            />
          </Card>
        </main>
      </div>
    </div>
  );
}
