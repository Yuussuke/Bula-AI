import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ArrowLeft, History, MessageSquarePlus, Pill, RefreshCw } from "lucide-react";
import { type ReactElement, useMemo } from "react";
import { Link } from "react-router-dom";

import { type ChatSessionResponse, listChatSessions } from "@/api/chat";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const CHAT_SESSION_LIST_LIMIT = 100;
const sessionDateFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
  timeZone: "America/Sao_Paulo",
});

interface ChatSessionNavigationProps {
  bulaId: string;
  currentSessionId: string | null;
  onStartNewSession: () => void;
  onNavigate?: () => void;
}

function compareSessionsByLastUpdate(
  firstSession: ChatSessionResponse,
  secondSession: ChatSessionResponse
): number {
  return Date.parse(secondSession.updated_at) - Date.parse(firstSession.updated_at);
}

function formatSessionDate(updatedAt: string): string {
  const parsedDate = new Date(updatedAt);
  if (Number.isNaN(parsedDate.getTime())) {
    return "";
  }

  return sessionDateFormatter.format(parsedDate);
}

export function ChatSessionNavigation({
  bulaId,
  currentSessionId,
  onStartNewSession,
  onNavigate,
}: ChatSessionNavigationProps): ReactElement {
  const sessionsQuery = useQuery({
    queryKey: ["chat-sessions", { limit: CHAT_SESSION_LIST_LIMIT, offset: 0 }],
    queryFn: () => listChatSessions({ limit: CHAT_SESSION_LIST_LIMIT, offset: 0 }),
  });
  const bulaSessions = useMemo(
    () =>
      (sessionsQuery.data ?? [])
        .filter((session) => session.bula_id === bulaId)
        .sort(compareSessionsByLastUpdate),
    [bulaId, sessionsQuery.data]
  );

  const handleStartNewSession = (): void => {
    onStartNewSession();
    onNavigate?.();
  };

  return (
    <div className="flex h-full flex-col">
      <div className="border-sidebar-border border-b p-5">
        <Link to="/" className="flex items-center gap-3" onClick={onNavigate}>
          <div className="bg-sidebar-primary/20 flex h-9 w-9 items-center justify-center rounded-xl">
            <Pill aria-hidden="true" className="text-sidebar-primary h-5 w-5" />
          </div>
          <div>
            <p className="font-semibold">Bula AI</p>
            <p className="text-sidebar-foreground/60 text-xs">Assistente de medicamentos</p>
          </div>
        </Link>
      </div>

      <div className="space-y-3 border-b p-4">
        <Button asChild variant="ghost" className="w-full justify-start gap-2">
          <Link to="/" onClick={onNavigate}>
            <ArrowLeft aria-hidden="true" className="h-4 w-4" />
            Voltar ao catálogo
          </Link>
        </Button>
        <Button
          type="button"
          variant={currentSessionId ? "secondary" : "default"}
          className="w-full justify-start gap-2"
          onClick={handleStartNewSession}
        >
          <MessageSquarePlus aria-hidden="true" className="h-4 w-4" />
          Nova conversa
        </Button>
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto p-4" aria-label="Conversas desta bula">
        <h2 className="text-sidebar-foreground/60 mb-3 flex items-center gap-2 px-2 text-xs font-semibold tracking-wide uppercase">
          <History aria-hidden="true" className="h-3.5 w-3.5" />
          Conversas desta bula
        </h2>

        {sessionsQuery.isLoading ? (
          <div role="status" aria-label="Carregando conversas" className="space-y-2">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        ) : null}

        {sessionsQuery.isError ? (
          <div className="border-sidebar-border rounded-lg border p-3 text-sm">
            <div className="flex items-start gap-2">
              <AlertCircle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
              <p>Não foi possível carregar suas conversas.</p>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="mt-2 gap-1.5"
              onClick={() => void sessionsQuery.refetch()}
            >
              <RefreshCw aria-hidden="true" className="h-3.5 w-3.5" />
              Tentar novamente
            </Button>
          </div>
        ) : null}

        {sessionsQuery.isSuccess && bulaSessions.length === 0 ? (
          <p className="text-sidebar-foreground/60 px-2 py-3 text-sm">
            Nenhuma conversa iniciada para esta bula.
          </p>
        ) : null}

        {bulaSessions.length > 0 ? (
          <ul className="space-y-1">
            {bulaSessions.map((session) => {
              const isCurrentSession = session.id === currentSessionId;

              return (
                <li key={session.id}>
                  <Link
                    to={`/bulas/${bulaId}/chat?session=${session.id}`}
                    replace
                    aria-current={isCurrentSession ? "page" : undefined}
                    onClick={onNavigate}
                    className={cn(
                      "block rounded-lg px-3 py-2.5 transition-colors",
                      isCurrentSession
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground/75 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
                    )}
                  >
                    <span className="block truncate text-sm font-medium">{session.title}</span>
                    <span className="mt-0.5 block text-xs opacity-65">
                      {formatSessionDate(session.updated_at)}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        ) : null}
      </nav>
    </div>
  );
}
