import { useInfiniteQuery } from "@tanstack/react-query";
import { AlertCircle, MessageSquarePlus, RefreshCw } from "lucide-react";
import { lazy, type ReactElement, Suspense } from "react";
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
const ConversationActions = lazy(() =>
  import("@/components/chat/conversation-actions").then((module) => ({
    default: module.ConversationActions,
  }))
);
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
  isCurrentSessionBusy?: boolean;
}

interface ConversationGroupProps extends RecentConversationsProps {
  scope: ChatScope | "pinned";
}

function ConversationGroup({
  scope,
  context,
  currentSessionId,
  onStartNewSession,
  onNavigate,
  returnTo,
  isCurrentSessionBusy = false,
}: ConversationGroupProps): ReactElement | null {
  const isPinned = scope === "pinned";
  const sessionsQuery = useInfiniteQuery({
    queryKey: ["chat-sessions", scope, { limit: PAGE_SIZE, sort: "updated_at", isPinned }],
    queryFn: ({ pageParam }) =>
      listChatSessions({
        scope: scope === "pinned" ? undefined : scope,
        isPinned,
        sort: "updated_at",
        limit: PAGE_SIZE,
        offset: pageParam,
      }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) =>
      lastPage.length === PAGE_SIZE ? pages.length * PAGE_SIZE : undefined,
  });
  const sessions = Array.from(
    new Map(
      (sessionsQuery.data?.pages.flat() ?? [])
        .filter(
          (session) =>
            (isPinned || (session.scope ?? "bula") === scope) &&
            Boolean(session.is_pinned) === isPinned &&
            ((session.scope ?? "bula") !== "cross_bula" || session.bula_id === null)
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
  if (isPinned && sessions.length === 0 && !sessionsQuery.isError) return null;

  return (
    <AccordionItem value={scope} className="border-sidebar-border">
      <AccordionTrigger
        className={cn(
          "px-2 py-3 text-sm hover:no-underline [&>svg]:text-current",
          isPinned && "text-sidebar-foreground/60 text-xs font-semibold tracking-wide uppercase"
        )}
      >
        {isPinned ? "Fixados" : scope === "cross_bula" ? "Chat geral" : "Por medicamento"}
      </AccordionTrigger>
      <AccordionContent className="space-y-2 pb-3">
        {isPinned ? null : canStartInCurrentContext ? (
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
              const scope = session.scope ?? "bula";
              const updatedAt = new Date(session.updated_at);
              const dateLabel = Number.isNaN(updatedAt.getTime())
                ? ""
                : sessionDateFormatter.format(updatedAt);
              const isUnavailable = scope === "bula" && session.bula_id === null;
              const isCurrentSession = session.id === currentSessionId;
              const isSameBula = context?.scope === "bula" && context.bulaId === session.bula_id;
              const parameters = catalogParameters(
                scope === "cross_bula" ? (session.catalog_scope ?? "all") : "all"
              );
              parameters.set("session", session.id);
              const content = (
                <>
                  <span className="block truncate text-sm font-medium">{session.title}</span>
                  {isUnavailable ? (
                    <span className="text-sidebar-foreground/60 text-xs">
                      Documento indisponível
                    </span>
                  ) : (
                    <time dateTime={session.updated_at} className="mt-0.5 block text-xs opacity-65">
                      {dateLabel}
                    </time>
                  )}
                </>
              );
              return (
                <li
                  key={session.id}
                  className={cn(
                    "flex flex-wrap items-start rounded-lg transition-colors",
                    isCurrentSession
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground/75 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                  )}
                >
                  {isUnavailable ? (
                    <div className="min-w-0 flex-1 px-3 py-2.5">{content}</div>
                  ) : (
                    <Link
                      to={`${scope === "cross_bula" ? "/chat" : `/bulas/${session.bula_id}/chat`}?${parameters.toString()}`}
                      state={isSameBula && returnTo ? { returnTo } : undefined}
                      aria-current={isCurrentSession ? "page" : undefined}
                      onClick={onNavigate}
                      title={session.title}
                      className="block min-w-0 flex-1 rounded-lg px-3 py-2.5"
                    >
                      {content}
                    </Link>
                  )}
                  <Suspense fallback={<span className="mt-1 mr-1 h-8 w-8 shrink-0" />}>
                    <ConversationActions
                      session={session}
                      isDisabled={isCurrentSession && isCurrentSessionBusy}
                      onDeleted={() => {
                        if (isCurrentSession) {
                          onStartNewSession?.();
                          onNavigate?.();
                        }
                      }}
                    />
                  </Suspense>
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
      <Accordion type="multiple" defaultValue={["pinned"]}>
        <ConversationGroup scope="pinned" {...props} />
      </Accordion>
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
