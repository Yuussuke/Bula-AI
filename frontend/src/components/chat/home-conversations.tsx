import { skipToken, useQuery } from "@tanstack/react-query";
import { ArrowRight, MessageSquareText, Pin } from "lucide-react";
import type { ReactElement } from "react";
import { Link } from "react-router-dom";

import { type ChatSessionResponse, getChatSession, listChatSessions } from "@/api/chat";
import { AnimatedIcon } from "@/components/ui/animated-icon";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { getChatSessionPath } from "@/lib/chat-navigation";
import { useAuthStore } from "@/store/auth";

const sessionDateFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
  timeZone: "America/Sao_Paulo",
});

function HomeConversationCard({
  session,
  userId,
  index,
}: {
  session: ChatSessionResponse;
  userId: number | undefined;
  index: number;
}): ReactElement {
  const scope = session.scope ?? "bula";
  const conversationPath = getChatSessionPath(session);
  const isUnavailable = conversationPath === null;
  const sessionQuery = useQuery({
    queryKey: ["chat-session", "home-preview", session.id, userId, session.updated_at],
    queryFn: isUnavailable ? skipToken : () => getChatSession(session.id),
  });
  const updatedAt = new Date(session.updated_at);
  const dateLabel = Number.isNaN(updatedAt.getTime()) ? "" : sessionDateFormatter.format(updatedAt);
  const latestQuestion = sessionQuery.data?.messages.findLast(
    (message) => message.role === "user" && message.content.trim().length > 0
  )?.content;
  const content = (
    <>
      <span className="flex items-start gap-3">
        <AnimatedIcon
          icon={session.is_pinned ? Pin : MessageSquareText}
          effect="conversation"
          className="text-primary mt-0.5 h-5 w-5"
        />
        <span className="line-clamp-2 min-w-0 flex-1 text-sm font-semibold [overflow-wrap:anywhere]">
          {session.title}
        </span>
        {!isUnavailable ? (
          <AnimatedIcon icon={ArrowRight} effect="send" className="text-primary mt-0.5" />
        ) : null}
      </span>
      {latestQuestion ? (
        <span className="text-muted-foreground line-clamp-2 text-sm [overflow-wrap:anywhere]">
          {latestQuestion}
        </span>
      ) : null}
      <span className="text-muted-foreground mt-auto flex flex-wrap items-center justify-between gap-2 text-xs">
        <span>{scope === "cross_bula" ? "Chat geral" : "Por medicamento"}</span>
        {dateLabel ? <time dateTime={session.updated_at}>{dateLabel}</time> : null}
      </span>
      {isUnavailable ? (
        <span className="text-muted-foreground text-xs">Documento indisponível</span>
      ) : null}
    </>
  );
  const className =
    "home-enter home-enter-up border-border/70 bg-card/55 flex h-full min-w-0 flex-col gap-3 rounded-2xl border p-5 backdrop-blur-[2px]";
  const style = { animationDelay: `${260 + index * 80}ms` };

  if (isUnavailable)
    return (
      <div className={className} style={style}>
        {content}
      </div>
    );

  return (
    <Link
      to={conversationPath}
      aria-label={`Continuar conversa ${session.title}`}
      className={`${className} hover:border-primary/35 focus-visible:ring-primary transition-[border-color,box-shadow] duration-200 hover:shadow-sm focus-visible:ring-2 focus-visible:outline-none`}
      style={style}
    >
      {content}
    </Link>
  );
}

export function HomeConversations(): ReactElement {
  return (
    <div className="space-y-8">
      <HomeConversationSection />
      <HomeConversationSection isPinned />
    </div>
  );
}

function HomeConversationSection({
  isPinned = false,
}: {
  isPinned?: boolean;
}): ReactElement | null {
  const userId = useAuthStore((state) => state.user?.id);
  const sessionsQuery = useQuery({
    queryKey: ["chat-sessions", "home", userId, isPinned],
    queryFn: () => listChatSessions({ limit: 3, sort: "updated_at", isPinned }),
    enabled: userId !== undefined,
  });
  const sessions = sessionsQuery.data ?? [];
  const label = isPinned ? "conversas fixadas" : "conversas recentes";
  const titleId = isPinned ? "home-pinned-title" : "home-conversations-title";
  if (isPinned && sessionsQuery.isSuccess && sessions.length === 0) return null;

  return (
    <section aria-labelledby={titleId} className="space-y-3">
      <h2
        id={titleId}
        className="text-muted-foreground text-xs font-semibold tracking-wider uppercase"
      >
        {isPinned ? "Conversas fixadas" : "Conversas recentes"}
      </h2>
      {sessionsQuery.isPending ? (
        <div role="status" aria-label={`Carregando ${label}`} className="grid gap-3 md:grid-cols-3">
          {[0, 1, 2].map((index) => (
            <Skeleton key={index} className="h-32 rounded-2xl" />
          ))}
        </div>
      ) : null}
      {sessionsQuery.isError ? (
        <div role="alert" className="text-muted-foreground text-sm">
          <p>Não foi possível carregar suas {label}.</p>
          <Button
            variant="link"
            className="h-auto px-0 py-2"
            onClick={() => void sessionsQuery.refetch()}
          >
            Tentar novamente
          </Button>
        </div>
      ) : null}
      {sessionsQuery.isSuccess && sessions.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          Suas próximas conversas aparecerão aqui para você continuar de onde parou.
        </p>
      ) : null}
      {sessionsQuery.isSuccess && sessions.length > 0 ? (
        <div className="-m-1 grid gap-3 overflow-hidden p-1 md:grid-cols-3">
          {sessions.map((session, index) => (
            <HomeConversationCard
              key={session.id}
              session={session}
              userId={userId}
              index={index}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}
