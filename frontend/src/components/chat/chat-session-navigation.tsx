import { type ReactElement, type ReactNode, useContext, useEffect } from "react";
import { createPortal } from "react-dom";

import type { ChatContext } from "@/api/chat";
import { RecentConversations } from "@/components/chat/recent-conversations";
import { ThemeToggle } from "@/components/theme-toggle";
import { WorkspaceSidebarContext } from "@/lib/workspace-sidebar-context";

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
  const targets = useContext(WorkspaceSidebarContext);
  useEffect(() => {
    if (!isDesktop || !targets) return;
    const { registerStartNewSession, setCatalogReturnTo } = targets;
    const unregister = registerStartNewSession(onStartNewSession);
    setCatalogReturnTo(returnTo.startsWith("/catalogo") ? returnTo : "/catalogo");
    return () => {
      unregister();
      setCatalogReturnTo(null);
    };
  }, [isDesktop, onStartNewSession, returnTo, targets]);

  const conversations = (
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
  );
  if (!isDesktop)
    return (
      <div className="flex h-full flex-col">
        {conversations}
        {children}
        <div className="border-sidebar-border border-t p-3">
          <ThemeToggle />
        </div>
      </div>
    );

  return (
    <>
      {targets?.content && createPortal(conversations, targets.content)}
      {targets?.footer && children && createPortal(children, targets.footer)}
      {targets?.rail && railControls && createPortal(railControls, targets.rail)}
    </>
  );
}
