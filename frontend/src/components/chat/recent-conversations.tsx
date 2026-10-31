import { useInfiniteQuery } from "@tanstack/react-query";
import { AlertCircle, MessageSquarePlus, RefreshCw } from "lucide-react";
import type { ReactElement } from "react";
import { Link } from "react-router-dom";

import { type ChatContext, type ChatScope, listChatSessions } from "@/api/chat";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { catalogParameters } from "@/lib/catalog-scope";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 10;
const sessionDateFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
  timeZone: "America/Sao_Paulo",
});

interface RecentConversationsProps {
  context?: ChatContext;
  currentSessionId?: string | null;
  onStartNewSession?: () => void;
  onNavigate?: () => void;
  returnTo?: string;
}

interface ConversationGroupProps extends RecentConversationsProps {
  scope: ChatScope;
}

function ConversationGroup({
  scope,
  context,
  currentSessionId,
  onStartNewSession,
  onNavigate,
  returnTo,
}: ConversationGroupProps): ReactElement {
  const sessionsQuery = useInfiniteQuery({
    queryKey: ["chat-sessions", scope, "recent", { limit: PAGE_SIZE, sort: "updated_at" }],
    queryFn: ({ pageParam }) =>
      listChatSessions({ scope, sort: "updated_at", limit: PAGE_SIZE, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) =>
      lastPage.length === PAGE_SIZE ? pages.length * PAGE_SIZE : undefined,
  });
  const sessions = Array.from(
    new Map(
      (sessionsQuery.data?.pages.flat() ?? [])
        .filter(
          (session) =>
            (session.scope ?? "bula") === scope &&
            (scope !== "cross_bula" || session.bula_id === null)
        )
        .map((session) => [session.id, session])
    ).values()
  );
  const canStartInCurrentContext = context?.scope === scope && onStartNewSession !== undefined;
  const startLabel = scope === "cross_bula" ? "Nova conversa geral" : "Nova conversa desta bula";
  const handleStartNewSession = (): void => {
    onStartNewSession?.();
    onNavigate?.();
  };

  return (
    <AccordionItem value={scope} className="border-sidebar-border">
      <AccordionTrigger className="px-2 py-3 text-sm hover:no-underline [&>svg]:text-current">
        {scope === "cross_bula" ? "Chat geral" : "Por medicamento"}
      </AccordionTrigger>
      <AccordionContent className="space-y-2 pb-3">
        {canStartInCurrentContext ? (
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2"
            onClick={handleStartNewSession}
          >
            <MessageSquarePlus aria-hidden="true" className="h-4 w-4" />
            {startLabel}
          </Button>
        ) : (
          <Button asChild variant="ghost" size="sm" className="w-full justify-start gap-2">
            <Link to={scope === "cross_bula" ? "/chat" : "/catalogo"} onClick={onNavigate}>
              <MessageSquarePlus aria-hidden="true" className="h-4 w-4" />
              {scope === "cross_bula" ? startLabel : "Escolher medicamento"}
            </Link>
          </Button>
        )}
        {scope === "bula" ? (
          <Link
            to="/minhas-bulas"
            onClick={onNavigate}
            className="text-sidebar-foreground/70 block rounded-md px-2 py-1 text-xs hover:underline"
          >
            Usar uma bula minha
          </Link>
        ) : null}
        {sessionsQuery.isPending ? (
          <div role="status" aria-label="Carregando conversas" className="space-y-2 px-2">
            <Skeleton className="bg-sidebar-accent h-12 w-full" />
            <Skeleton className="bg-sidebar-accent h-12 w-full" />
          </div>
        ) : null}
        {sessionsQuery.isError ? (
          <div role="alert" className="px-2 text-xs">
            <p className="flex items-start gap-2">
              <AlertCircle aria-hidden="true" className="h-4 w-4 shrink-0" />
              Não foi possível carregar suas conversas.
            </p>
            <Button
              variant="ghost"
              size="sm"
              className="mt-1 gap-2"
              onClick={() => void sessionsQuery.refetch()}
            >
              <RefreshCw aria-hidden="true" className="h-3.5 w-3.5" />
              Tentar novamente
            </Button>
          </div>
        ) : null}
        {sessionsQuery.isSuccess && sessions.length === 0 ? (
          <p className="text-sidebar-foreground/60 px-2 py-2 text-xs">Nenhuma conversa recente.</p>
        ) : null}
        {sessions.length > 0 ? (
          <ul className="space-y-1">
            {sessions.map((session) => {
              const updatedAt = new Date(session.updated_at);
              const dateLabel = Number.isNaN(updatedAt.getTime())
                ? ""
                : sessionDateFormatter.format(updatedAt);
              if (scope === "bula" && session.bula_id === null) {
                return (
                  <li key={session.id} className="text-sidebar-foreground/60 px-3 py-2 text-xs">
                    <span className="block truncate">{session.title}</span>
                    <span>Documento indisponível</span>
                  </li>
                );
              }
              const isCurrentSession = session.id === currentSessionId;
              const isSameBula = context?.scope === "bula" && context.bulaId === session.bula_id;
              const parameters = catalogParameters(
                scope === "cross_bula" ? (session.catalog_scope ?? "all") : "all"
              );
              parameters.set("session", session.id);
              return (
                <li key={session.id}>
                  <Link
                    to={`${scope === "cross_bula" ? "/chat" : `/bulas/${session.bula_id}/chat`}?${parameters.toString()}`}
                    state={isSameBula && returnTo ? { returnTo } : undefined}
                    aria-current={isCurrentSession ? "page" : undefined}
                    onClick={onNavigate}
                    title={session.title}
                    className={cn(
                      "block rounded-lg px-3 py-2.5 transition-colors",
                      isCurrentSession
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground/75 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                    )}
                  >
                    <span className="block truncate text-sm font-medium">{session.title}</span>
                    <time dateTime={session.updated_at} className="mt-0.5 block text-xs opacity-65">
                      {dateLabel}
                    </time>
                  </Link>
                </li>
              );
            })}
          </ul>
        ) : null}
        {sessionsQuery.hasNextPage ? (
          <Button
            variant="ghost"
            size="sm"
            className="w-full"
            disabled={sessionsQuery.isFetchingNextPage}
            onClick={() => void sessionsQuery.fetchNextPage()}
          >
            {sessionsQuery.isFetchingNextPage ? "Carregando…" : "Mostrar mais conversas"}
          </Button>
        ) : null}
      </AccordionContent>
    </AccordionItem>
  );
}

export function RecentConversations(props: RecentConversationsProps): ReactElement {
  return (
    <nav aria-label="Conversas recentes" className="px-3 py-2">
      <p className="text-sidebar-foreground/60 px-2 py-2 text-xs font-semibold tracking-wide uppercase">
        Conversas recentes
      </p>
      <Accordion type="multiple" defaultValue={["cross_bula", "bula"]}>
        <ConversationGroup scope="cross_bula" {...props} />
        <ConversationGroup scope="bula" {...props} />
      </Accordion>
    </nav>
  );
}
