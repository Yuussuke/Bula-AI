import { ArrowLeft, Pill } from "lucide-react";
import { type ReactElement, type ReactNode } from "react";
import { Link } from "react-router-dom";

import type { ChatContext } from "@/api/chat";
import { RecentConversations } from "@/components/chat/recent-conversations";
import { Button } from "@/components/ui/button";

interface ChatSessionNavigationProps {
  context: ChatContext;
  currentSessionId: string | null;
  onStartNewSession: () => void;
  onNavigate?: () => void;
  returnTo?: string;
  children?: ReactNode;
}

export function ChatSessionNavigation({
  context,
  currentSessionId,
  onStartNewSession,
  onNavigate,
  returnTo = "/",
  children,
}: ChatSessionNavigationProps): ReactElement {
  return (
    <div className="flex h-full flex-col">
      <div className="border-sidebar-border shrink-0 border-b p-5">
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

      <div className="border-sidebar-border shrink-0 space-y-3 border-b p-4">
        <Button asChild variant="ghost" className="w-full justify-start gap-2">
          <Link to={returnTo} onClick={onNavigate}>
            <ArrowLeft aria-hidden="true" className="h-4 w-4" />
            {returnTo.startsWith("/catalogo")
              ? "Voltar ao catálogo"
              : returnTo === "/minhas-bulas"
                ? "Voltar às minhas bulas"
                : "Voltar ao início"}
          </Link>
        </Button>
      </div>

      <div className="sidebar-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain">
        <RecentConversations
          context={context}
          currentSessionId={currentSessionId}
          onStartNewSession={onStartNewSession}
          onNavigate={onNavigate}
          returnTo={returnTo}
        />
      </div>
      {children ? (
        <div className="border-sidebar-border shrink-0 border-t p-4">{children}</div>
      ) : null}
    </div>
  );
}
