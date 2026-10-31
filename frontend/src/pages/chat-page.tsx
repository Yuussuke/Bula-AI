import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ArrowLeft, History } from "lucide-react";
import { lazy, type ReactElement, Suspense, useState } from "react";
import { Link, Navigate, useLocation, useParams, useSearchParams } from "react-router-dom";

import { getQueryableBula } from "@/api/bulas";
import type { ChatContext, ChatScope } from "@/api/chat";
import { CatalogSelector } from "@/components/bulas/catalog-selector";
import { ChatComposer } from "@/components/chat/chat-composer";
import { ChatMessageList } from "@/components/chat/chat-message-list";
import { ChatSessionNavigation } from "@/components/chat/chat-session-navigation";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useChatSession } from "@/hooks/use-chat-session";
import { useIsMobile } from "@/hooks/use-mobile";
import { ApiError } from "@/lib/api";
import { catalogParameters, type CatalogScope, readCatalogScope } from "@/lib/catalog-scope";
import { cn } from "@/lib/utils";
import { useSidebarStore } from "@/store/sidebar";

const ModeSelector = lazy(() =>
  import("@/components/chat/mode-selector").then((module) => ({ default: module.ModeSelector }))
);

function isNotFoundError(error: Error | null): boolean {
  return error instanceof ApiError && error.status === 404;
}

function ChatPageLoadingState(): ReactElement {
  const isSidebarCollapsed = useSidebarStore((state) => state.isCollapsed);
  return (
    <div
      role="status"
      aria-label="Carregando conversa"
      className="bg-background flex h-dvh overflow-hidden"
    >
      <span className="sr-only">Carregando conversa…</span>

      <aside
        className="bg-sidebar border-sidebar-border hidden shrink-0 overflow-hidden border-r lg:block"
        style={{ width: isSidebarCollapsed ? 56 : 288 }}
      >
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
        <header className="bg-card border-border border-b lg:hidden">
          <div className="mx-auto flex max-w-5xl items-center gap-3 px-3 py-3 sm:px-6 sm:py-4">
            <Skeleton className="h-9 w-9 lg:hidden" />
            <div className="min-w-0 flex-1 space-y-2">
              <Skeleton className="h-5 w-full max-w-sm" />
              <Skeleton className="h-4 w-full max-w-lg" />
            </div>
            <Skeleton className="h-7 w-32" />
          </div>
        </header>

        <main className="flex min-h-0 flex-1 flex-col">
          <div className="mx-auto w-full max-w-3xl flex-1 space-y-6 p-4 sm:p-5">
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
          <div className="mx-auto flex w-full max-w-3xl gap-3 p-4">
            <Skeleton className="h-11 flex-1" />
            <Skeleton className="h-11 w-11" />
          </div>
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

export function ChatPage({ scope = "bula" }: { scope?: ChatScope }): ReactElement {
  const { bulaId } = useParams<{ bulaId: string }>();
  const location = useLocation();
  const navigationState: unknown = location.state;
  const catalogReturnTo =
    typeof navigationState === "object" &&
    navigationState !== null &&
    "returnTo" in navigationState &&
    typeof navigationState.returnTo === "string" &&
    /^\/catalogo(?:\?|$)/.test(navigationState.returnTo)
      ? navigationState.returnTo
      : null;
  const [searchParams, setSearchParams] = useSearchParams();
  const [question, setQuestion] = useState("");
  const [isMobileSessionsOpen, setIsMobileSessionsOpen] = useState(false);
  const isCompactLayout = useIsMobile(1024);
  const sessionId = searchParams.get("session");
  const requestedCatalogScope = readCatalogScope(searchParams.get("catalogo"));
  const resolvedBulaId = bulaId ?? "";
  const context: ChatContext =
    scope === "cross_bula" ? { scope: "cross_bula" } : { scope: "bula", bulaId: resolvedBulaId };

  const bulaQuery = useQuery({
    queryKey: ["queryable-bula", resolvedBulaId],
    queryFn: () => getQueryableBula(resolvedBulaId),
    enabled: scope === "bula" && Boolean(bulaId),
    staleTime: 5 * 60 * 1000,
  });
  const chatSession = useChatSession({
    catalogScope: requestedCatalogScope,
    context,
    sessionId,
    onSessionCreated: (createdSessionId) => {
      const parameters = catalogParameters(requestedCatalogScope);
      parameters.set("session", createdSessionId);
      setSearchParams(parameters, { replace: true, state: navigationState });
    },
  });

  const handleSendQuestion = (): void => {
    const cleanQuestion = question.trim();
    if (!cleanQuestion) {
      return;
    }

    setQuestion("");
    void chatSession.sendQuestion(cleanQuestion).then((wasSent) => {
      if (wasSent === false) {
        setQuestion((currentQuestion) => currentQuestion || cleanQuestion);
      }
    });
  };

  const handleStartNewSession = (): void => {
    chatSession.invalidatePendingConversation();
    setQuestion("");
    setSearchParams(catalogParameters(chatSession.catalogScope), {
      replace: true,
      state: navigationState,
    });
  };

  const handleCatalogChange = (selected: CatalogScope): void => {
    if (selected === chatSession.catalogScope || chatSession.isSending) return;
    chatSession.invalidatePendingConversation();
    setSearchParams(catalogParameters(selected), { replace: true, state: navigationState });
  };

  if (scope === "bula" && !bulaId) {
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

  if (chatSession.hasContextMismatch) {
    return (
      <ChatPageUnavailable message="Esta conversa pertence a outra bula ou contexto e não pode ser aberta nesta página." />
    );
  }

  if (bulaQuery.error || chatSession.loadError || (scope === "bula" && !bulaQuery.data)) {
    return (
      <ChatPageUnavailable message="Não foi possível carregar a conversa. Verifique a conexão e tente novamente." />
    );
  }

  const bula = bulaQuery.data;
  const bulaDisplayName = scope === "cross_bula" ? "Chat geral" : bula?.alias || bula?.product_name;
  const bulaDescription = [
    bula?.alias ? bula.product_name : bula?.active_ingredient,
    bula?.strength,
    bula?.manufacturer,
  ]
    .filter((value): value is string => Boolean(value))
    .join(" · ");

  const returnTo =
    scope === "cross_bula"
      ? `/catalogo?${catalogParameters(chatSession.catalogScope).toString()}`
      : bula?.corpus === "private"
        ? "/minhas-bulas"
        : (catalogReturnTo ?? "/catalogo");
  const selectSuggestion = (suggestion: string): void => {
    setQuestion(suggestion);
    document.getElementById("chat-question")?.focus();
  };

  const renderChatControls = (variant: "compact" | "icon", isSidebar: boolean): ReactElement => (
    <div className={cn("flex flex-wrap items-center gap-1", variant === "icon" && "flex-col")}>
      {scope === "cross_bula" ? (
        <CatalogSelector
          value={chatSession.catalogScope}
          onChange={handleCatalogChange}
          isDisabled={chatSession.isSending}
          isSidebar={isSidebar}
          variant={variant}
        />
      ) : null}
      <Suspense fallback={<Skeleton className="h-9 w-16" />}>
        <ModeSelector
          value={chatSession.mode}
          onChange={chatSession.setMode}
          isDisabled={chatSession.isSending}
          isSidebar={isSidebar}
          variant={variant}
        />
      </Suspense>
    </div>
  );

  const sidebarDetails = (
    <div className="space-y-2">
      {scope !== "cross_bula" ? (
        <details className="text-sidebar-foreground/70 text-xs">
          <summary className="cursor-pointer truncate py-1">{bulaDisplayName}</summary>
          <p className="mt-1 max-h-32 overflow-y-auto leading-relaxed break-words">
            {bulaDescription || "Documento enviado por você"}
          </p>
        </details>
      ) : null}
      {renderChatControls("compact", true)}
    </div>
  );

  return (
    <div className="bg-background flex h-dvh overflow-hidden">
      {!isCompactLayout ? (
        <ChatSessionNavigation
          context={context}
          currentSessionId={sessionId}
          onStartNewSession={handleStartNewSession}
          returnTo={returnTo}
          isDesktop
          isCurrentSessionBusy={chatSession.isSending}
          railControls={renderChatControls("icon", true)}
        >
          {sidebarDetails}
        </ChatSessionNavigation>
      ) : null}

      <Sheet open={isMobileSessionsOpen} onOpenChange={setIsMobileSessionsOpen}>
        <SheetContent
          side="left"
          className="bg-sidebar text-sidebar-foreground w-[85%] max-w-80 gap-0 p-0"
        >
          <SheetHeader className="sr-only">
            <SheetTitle>
              {scope === "cross_bula" ? "Conversas gerais" : "Conversas desta bula"}
            </SheetTitle>
            <SheetDescription>Abra uma conversa anterior ou inicie outra.</SheetDescription>
          </SheetHeader>
          <ChatSessionNavigation
            context={context}
            currentSessionId={sessionId}
            onStartNewSession={handleStartNewSession}
            returnTo={returnTo}
            onNavigate={() => setIsMobileSessionsOpen(false)}
            isCurrentSessionBusy={chatSession.isSending}
          ></ChatSessionNavigation>
        </SheetContent>
      </Sheet>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        {isCompactLayout ? (
          <header className="bg-background border-border shrink-0 border-b">
            <div className="flex items-center gap-2 px-3 py-2">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label="Abrir conversas"
                onClick={() => setIsMobileSessionsOpen(true)}
              >
                <History aria-hidden="true" className="h-5 w-5" />
              </Button>
              <Button asChild variant="ghost" size="icon" aria-label="Voltar para as bulas">
                <Link to={returnTo}>
                  <ArrowLeft aria-hidden="true" className="h-5 w-5" />
                </Link>
              </Button>
              <p className="min-w-0 flex-1 truncate text-sm font-medium">{bulaDisplayName}</p>
              {renderChatControls("compact", false)}
            </div>
          </header>
        ) : null}

        <main className="flex min-h-0 w-full flex-1 flex-col overflow-hidden">
          <h1 className="sr-only">{bulaDisplayName}</h1>
          {chatSession.modeWarning ? (
            <p
              role="status"
              className="text-muted-foreground mx-auto w-full max-w-3xl shrink-0 px-4 py-2 text-sm"
            >
              {chatSession.modeWarning}
            </p>
          ) : null}
          {sessionId && chatSession.messages.length === 0 ? (
            <Alert className="m-4 w-auto">
              <AlertCircle aria-hidden="true" />
              <AlertTitle>Conversa sem mensagens</AlertTitle>
              <AlertDescription>
                Esta sessão ainda não possui mensagens. Envie uma pergunta para começar.
              </AlertDescription>
            </Alert>
          ) : null}
          <ChatMessageList
            messages={chatSession.messages}
            isResponding={chatSession.isSending}
            scope={scope}
            onSuggestionSelected={selectSuggestion}
          />
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
            scope={scope}
            value={question}
            isDisabled={chatSession.isSending}
            onChange={setQuestion}
            onSubmit={handleSendQuestion}
          />
        </main>
      </div>
    </div>
  );
}
