import { useMutation } from "@tanstack/react-query";
import {
  BookOpenText,
  ClipboardCheck,
  Files,
  History,
  House,
  Library,
  LogOut,
  Menu,
  MessageSquarePlus,
  Users,
} from "lucide-react";
import { type ReactElement, useCallback, useMemo, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { BrandLogo } from "@/components/brand-logo";
import { RecentConversations } from "@/components/chat/recent-conversations";
import { ThemeToggle } from "@/components/theme-toggle";
import { ActionHint } from "@/components/ui/action-hint";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { sidebarShortcutClass, WorkspaceSidebar } from "@/components/workspace-sidebar";
import { useIsMobile } from "@/hooks/use-mobile";
import { logoutRequest } from "@/lib/api";
import { readCatalogReturnTo } from "@/lib/catalog-scope";
import { queryClient } from "@/lib/queryClient";
import { cn } from "@/lib/utils";
import { WorkspaceSidebarContext } from "@/lib/workspace-sidebar-context";
import { useAuthStore } from "@/store/auth";
import { useSidebarStore } from "@/store/sidebar";

const navigation = [
  { path: "/", label: "Início", icon: House },
  { path: "/minhas-bulas", label: "Minhas bulas", icon: Library },
  { path: "/catalogo", label: "Catálogo Geral", icon: BookOpenText },
];

export function DashboardView(): ReactElement {
  const navigate = useNavigate();
  const location = useLocation();
  const { pathname } = location;
  const isChatPage = pathname === "/chat" || /^\/bulas\/[^/]+\/chat$/.test(pathname);
  const isIndividualChat = isChatPage && pathname !== "/chat";
  const Content = isChatPage ? "div" : "main";
  const startNewSession = useRef<(() => void) | null>(null);
  const registerStartNewSession = useCallback((action: () => void): (() => void) => {
    startNewSession.current = action;
    return () => {
      if (startNewSession.current === action) startNewSession.current = null;
    };
  }, []);
  const [sidebarContent, setSidebarContent] = useState<HTMLDivElement | null>(null);
  const [sidebarFooter, setSidebarFooter] = useState<HTMLDivElement | null>(null);
  const [sidebarRail, setSidebarRail] = useState<HTMLDivElement | null>(null);
  const [catalogReturnTo, setCatalogReturnTo] = useState<string | null>(null);
  const sidebarTargets = useMemo(
    () => ({
      content: sidebarContent,
      footer: sidebarFooter,
      rail: sidebarRail,
      registerStartNewSession,
      setCatalogReturnTo,
    }),
    [registerStartNewSession, sidebarContent, sidebarFooter, sidebarRail]
  );
  const setCollapsed = useSidebarStore((state) => state.setCollapsed);
  const user = useAuthStore((state) => state.user);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const isCompactLayout = useIsMobile(1024);
  const visibleNavigation = [
    ...navigation,
    { path: "/compartilhadas", label: "Bulas compartilhadas", icon: Files },
  ];
  if (user?.role === "reviewer" || user?.role === "admin")
    visibleNavigation.push({ path: "/curadoria", label: "Curadoria", icon: ClipboardCheck });
  if (user?.role === "admin")
    visibleNavigation.push({
      path: "/administracao/usuarios",
      label: "Perfis de acesso",
      icon: Users,
    });
  const logoutMutation = useMutation({
    mutationFn: logoutRequest,
    onSettled: () => {
      clearAuth();
      queryClient.clear();
      void navigate("/auth", { replace: true });
    },
  });

  const renderSidebarContent = (): ReactElement => (
    <>
      <Link
        to="/"
        onClick={() => setIsMobileMenuOpen(false)}
        className="border-sidebar-border flex items-center gap-3 border-b px-5 py-5"
      >
        <BrandLogo variant="white" className="h-10 w-12" />
        <span>
          <span className="block text-lg font-bold">Bula AI</span>
          <span className="text-sidebar-foreground/60 text-xs">Informação com fontes</span>
        </span>
      </Link>
      <div className="sidebar-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain">
        <nav className="space-y-1 p-3" aria-label="Navegação principal">
          {visibleNavigation.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              end
              onClick={() => setIsMobileMenuOpen(false)}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-3 text-sm transition-colors",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                    : "text-sidebar-foreground/75 hover:bg-sidebar-accent/50"
                )
              }
            >
              <Icon aria-hidden="true" className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <RecentConversations onNavigate={() => setIsMobileMenuOpen(false)} />
      </div>
      <div className="border-sidebar-border border-t p-4">
        <ThemeToggle />
        <p className="truncate text-sm font-medium">{user?.name ?? "Usuário"}</p>
        <p className="text-sidebar-foreground/60 truncate text-xs">{user?.email}</p>
      </div>
    </>
  );

  return (
    <WorkspaceSidebarContext.Provider value={sidebarTargets}>
      <div className="bg-background flex h-dvh overflow-hidden">
        {!isCompactLayout ? (
          <WorkspaceSidebar
            navigationLabel="Navegação principal"
            collapsedControls={isChatPage ? <div ref={setSidebarRail} /> : undefined}
            shortcuts={
              <>
                <ActionHint
                  label={isIndividualChat ? "Nova conversa desta bula" : "Nova conversa geral"}
                >
                  <Button
                    variant="ghost"
                    size="icon"
                    className={sidebarShortcutClass}
                    aria-label={
                      isIndividualChat
                        ? "Iniciar nova conversa desta bula"
                        : "Iniciar nova conversa geral"
                    }
                    onClick={() =>
                      startNewSession.current ? startNewSession.current() : void navigate("/chat")
                    }
                  >
                    <MessageSquarePlus aria-hidden="true" />
                  </Button>
                </ActionHint>
                {visibleNavigation
                  .filter((item) => item.path !== "/")
                  .map(({ path, label, icon: Icon }) => (
                    <ActionHint
                      key={path}
                      label={
                        path === "/catalogo" && isChatPage ? "Explorar catálogo de bulas" : label
                      }
                    >
                      <NavLink
                        to={
                          path === "/catalogo" && isChatPage
                            ? (catalogReturnTo ?? readCatalogReturnTo(location.state) ?? path)
                            : path
                        }
                        end
                        aria-label={
                          path === "/catalogo" && isChatPage ? "Explorar catálogo de bulas" : label
                        }
                        className={cn(
                          sidebarShortcutClass,
                          "aria-[current=page]:bg-sidebar-accent aria-[current=page]:text-sidebar-accent-foreground"
                        )}
                      >
                        <Icon aria-hidden="true" className="h-4 w-4" />
                      </NavLink>
                    </ActionHint>
                  ))}
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
            <div ref={setSidebarContent} className="flex min-h-0 flex-1 flex-col">
              {!isChatPage ? (
                <div className="sidebar-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain pt-2">
                  <RecentConversations />
                </div>
              ) : null}
            </div>
            <div
              ref={setSidebarFooter}
              className={isChatPage ? "border-sidebar-border shrink-0 border-t p-3" : "hidden"}
            />
          </WorkspaceSidebar>
        ) : null}
        <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
          <SheetContent side="left" className="bg-sidebar text-sidebar-foreground w-64 p-0">
            <SheetHeader className="sr-only">
              <SheetTitle>Menu de navegação</SheetTitle>
              <SheetDescription>
                Acesse suas bulas, o catálogo de fontes e o chat geral.
              </SheetDescription>
            </SheetHeader>
            <div className="flex h-full flex-col">{renderSidebarContent()}</div>
          </SheetContent>
        </Sheet>
        <div className="@container relative isolate flex min-w-0 flex-1 flex-col">
          <div
            className={cn(
              "pointer-events-none absolute inset-x-0 top-3 z-20 flex items-center gap-2 px-4 sm:gap-4 sm:px-6",
              isChatPage && isCompactLayout && "hidden"
            )}
          >
            <div className="pointer-events-auto">
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                className="lg:hidden"
                onClick={() => setIsMobileMenuOpen(true)}
                aria-label="Abrir menu"
              >
                <Menu aria-hidden="true" className="h-5 w-5" />
              </Button>
            </div>
            <div className="min-w-0 flex-1" />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="bg-background/90 pointer-events-auto backdrop-blur-sm"
              onClick={() => logoutMutation.mutate()}
              disabled={logoutMutation.isPending}
            >
              <LogOut aria-hidden="true" className="mr-2 h-4 w-4" />
              {logoutMutation.isPending ? "Saindo..." : "Sair"}
            </Button>
          </div>
          <Content
            className={cn(
              isChatPage
                ? cn("min-h-0 flex-1 overflow-hidden", !isCompactLayout && "pt-16")
                : "clean-scroll min-h-0 flex-1 overflow-y-auto p-4 pt-16 sm:p-6 sm:pt-16 lg:p-8 lg:pt-16",
              pathname === "/" && "overflow-x-hidden"
            )}
          >
            <div
              key={pathname}
              className={cn("page-transition", isChatPage ? "h-full" : "mx-auto w-full max-w-6xl")}
            >
              <Outlet />
            </div>
          </Content>
        </div>
      </div>
    </WorkspaceSidebarContext.Provider>
  );
}
