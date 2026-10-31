import { BookOpenText, Files, History, MessageSquarePlus } from "lucide-react";
import type { ReactElement, ReactNode } from "react";
import { Link } from "react-router-dom";

import type { ChatContext } from "@/api/chat";
import { RecentConversations } from "@/components/chat/recent-conversations";
import { ActionHint } from "@/components/ui/action-hint";
import { Button } from "@/components/ui/button";
import { sidebarShortcutClass, WorkspaceSidebar } from "@/components/workspace-sidebar";
import { useSidebarStore } from "@/store/sidebar";

interface ChatSessionNavigationProps {
  context: ChatContext;
  currentSessionId: string | null;
  onStartNewSession: () => void;
  onNavigate?: () => void;
  returnTo?: string;
  children?: ReactNode;
  railControls?: ReactNode;
  isDesktop?: boolean;
  isCurrentSessionBusy?: boolean;
}

export function ChatSessionNavigation({
  context,
  currentSessionId,
  onStartNewSession,
  onNavigate,
  returnTo = "/",
  children,
  railControls,
  isDesktop = false,
  isCurrentSessionBusy = false,
}: ChatSessionNavigationProps): ReactElement {
  const setCollapsed = useSidebarStore((state) => state.setCollapsed);
  const conversations = (
    <>
      <div className="sidebar-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain pt-2">
        <RecentConversations
          context={context}
          currentSessionId={currentSessionId}
          onStartNewSession={onStartNewSession}
          onNavigate={onNavigate}
          returnTo={returnTo}
          isCurrentSessionBusy={isCurrentSessionBusy}
        />
      </div>
      {children ? (
        <div className="border-sidebar-border shrink-0 border-t p-3">{children}</div>
      ) : null}
    </>
  );
  if (!isDesktop)
    return (
      <div className="flex h-full flex-col">
        {conversations}
        <div className="border-sidebar-border border-t p-3"></div>
      </div>
    );
  return (
    <WorkspaceSidebar
      collapsedControls={railControls}
      shortcuts={
        <>
          <ActionHint
            label={
              context.scope === "cross_bula" ? "Nova conversa geral" : "Nova conversa desta bula"
            }
          >
            <Button
              variant="ghost"
              size="icon"
              className={sidebarShortcutClass}
              aria-label={
                context.scope === "cross_bula"
                  ? "Iniciar nova conversa geral"
                  : "Iniciar nova conversa desta bula"
              }
              onClick={onStartNewSession}
            >
              <MessageSquarePlus aria-hidden="true" />
            </Button>
          </ActionHint>
          <ActionHint label="Explorar catálogo de bulas">
            <Button asChild variant="ghost" size="icon" className={sidebarShortcutClass}>
              <Link
                to={returnTo.startsWith("/catalogo") ? returnTo : "/catalogo"}
                aria-label="Explorar catálogo de bulas"
              >
                <BookOpenText aria-hidden="true" />
              </Link>
            </Button>
          </ActionHint>
          <ActionHint label="Minhas bulas">
            <Button asChild variant="ghost" size="icon" className={sidebarShortcutClass}>
              <Link to="/minhas-bulas" aria-label="Minhas bulas">
                <Files aria-hidden="true" />
              </Link>
            </Button>
          </ActionHint>
          <ActionHint label="Conversas recentes">
            <Button
              variant="ghost"
              size="icon"
              className={sidebarShortcutClass}
              aria-label="Mostrar conversas recentes"
              onClick={() => setCollapsed(false)}
            >
              <History aria-hidden="true" />
            </Button>
          </ActionHint>
        </>
      }
    >
      {conversations}
    </WorkspaceSidebar>
  );
}
