import { useMutation } from "@tanstack/react-query";
import { BookOpenText, House, Library, LogOut, Menu, Pill } from "lucide-react";
import { type ReactElement, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { RecentConversations } from "@/components/chat/recent-conversations";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { logoutRequest } from "@/lib/api";
import { queryClient } from "@/lib/queryClient";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

const navigation = [
  { path: "/", label: "Início", icon: House },
  { path: "/minhas-bulas", label: "Minhas bulas", icon: Library },
  { path: "/catalogo", label: "Catálogo ANVISA", icon: BookOpenText },
];

export function DashboardView(): ReactElement {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((state) => state.user);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const title = navigation.find((item) => item.path === location.pathname)?.label ?? "Bula AI";
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
        <span className="bg-sidebar-primary/20 rounded-xl p-2.5">
          <Pill aria-hidden="true" className="text-sidebar-primary h-5 w-5" />
        </span>
        <span>
          <span className="block text-lg font-bold">Bula AI</span>
          <span className="text-sidebar-foreground/60 text-xs">Informação com fontes</span>
        </span>
      </Link>
      <div className="sidebar-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain">
        <nav className="space-y-1 p-3" aria-label="Navegação principal">
          {navigation.map(({ path, label, icon: Icon }) => (
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
        <p className="truncate text-sm font-medium">{user?.name ?? "Usuário"}</p>
        <p className="text-sidebar-foreground/60 truncate text-xs">{user?.email}</p>
      </div>
    </>
  );

  return (
    <div className="bg-background flex h-dvh overflow-hidden">
      <aside className="bg-sidebar text-sidebar-foreground border-sidebar-border hidden w-60 shrink-0 flex-col border-r md:flex">
        {renderSidebarContent()}
      </aside>
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
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-border bg-card flex min-h-16 shrink-0 items-center justify-between gap-3 border-b px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className="md:hidden"
              onClick={() => setIsMobileMenuOpen(true)}
              aria-label="Abrir menu"
            >
              <Menu aria-hidden="true" className="h-5 w-5" />
            </Button>
            <p className="truncate font-medium">{title}</p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => logoutMutation.mutate()}
            disabled={logoutMutation.isPending}
          >
            <LogOut aria-hidden="true" className="mr-2 h-4 w-4" />
            {logoutMutation.isPending ? "Saindo..." : "Sair"}
          </Button>
        </header>
        <main className="clean-scroll min-h-0 flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="mx-auto w-full max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
