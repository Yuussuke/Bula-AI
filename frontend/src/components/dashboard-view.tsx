"use client";

import { useMutation } from "@tanstack/react-query";
import { BookOpenText, LogOut, Menu, Pill } from "lucide-react";
import { type ReactElement, useState } from "react";
import { useNavigate } from "react-router-dom";

import { SystemBulaCatalog } from "@/components/bulas/system-bula-catalog";
import { SystemBulaNavigation } from "@/components/bulas/system-bula-navigation";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { logoutRequest } from "@/lib/api";
import { queryClient } from "@/lib/queryClient";
import { useAuthStore } from "@/store/auth";

export function DashboardView(): ReactElement {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const logoutMutation = useMutation({
    mutationFn: logoutRequest,
    onSettled: () => {
      clearAuth();
      queryClient.clear();
      void navigate("/auth", { replace: true });
    },
  });

  const userInitials =
    user?.name
      .split(" ")
      .filter(Boolean)
      .map((namePart) => namePart.charAt(0))
      .join("")
      .slice(0, 2)
      .toUpperCase() ?? "US";

  const renderSidebarContent = (): ReactElement => (
    <>
      <div className="border-sidebar-border border-b p-6">
        <div className="flex items-center gap-3">
          <div className="bg-sidebar-primary/20 flex h-10 w-10 items-center justify-center rounded-xl">
            <Pill aria-hidden="true" className="text-sidebar-primary h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold">Bula AI</h1>
            <p className="text-sidebar-foreground/60 text-xs">Assistente de medicamentos</p>
          </div>
        </div>
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto p-4" aria-label="Navegação principal">
        <div className="bg-sidebar-accent text-sidebar-accent-foreground flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium">
          <BookOpenText aria-hidden="true" className="h-5 w-5" />
          Catálogo de bulas
        </div>
        <SystemBulaNavigation onNavigate={() => setIsMobileMenuOpen(false)} />
      </nav>

      <div className="border-sidebar-border border-t p-4">
        <div className="bg-sidebar-accent/30 flex items-center gap-3 rounded-lg px-2 py-2">
          <div className="bg-sidebar-primary/20 text-sidebar-primary flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium">
            {userInitials}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{user?.name ?? "Usuário"}</p>
            <p className="text-sidebar-foreground/60 truncate text-xs">
              {user?.email ?? "E-mail não disponível"}
            </p>
          </div>
        </div>
      </div>
    </>
  );

  return (
    <div className="bg-background flex min-h-screen">
      <aside className="bg-sidebar text-sidebar-foreground border-sidebar-border hidden w-72 shrink-0 flex-col border-r md:flex">
        {renderSidebarContent()}
      </aside>

      <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
        <SheetContent side="left" className="bg-sidebar text-sidebar-foreground w-72 p-0">
          <SheetHeader className="sr-only">
            <SheetTitle>Menu de navegação</SheetTitle>
          </SheetHeader>
          <div className="flex h-full flex-col">{renderSidebarContent()}</div>
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-border bg-card flex min-h-16 items-center justify-between gap-4 border-b px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className="md:hidden"
              onClick={() => setIsMobileMenuOpen(true)}
            >
              <Menu aria-hidden="true" className="h-5 w-5" />
              <span className="sr-only">Abrir menu</span>
            </Button>
            <div className="min-w-0">
              <h2 className="truncate text-base font-semibold sm:text-lg">Catálogo de bulas</h2>
              <p className="text-muted-foreground hidden text-xs sm:block sm:text-sm">
                Bulas publicadas, revisadas e prontas para consulta
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <Avatar className="h-9 w-9">
              <AvatarFallback className="bg-primary/10 text-primary text-sm font-medium">
                {userInitials}
              </AvatarFallback>
            </Avatar>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => logoutMutation.mutate()}
              disabled={logoutMutation.isPending}
            >
              <LogOut aria-hidden="true" className="h-4 w-4 sm:mr-2" />
              <span className="sr-only sm:not-sr-only">
                {logoutMutation.isPending ? "Saindo..." : "Sair"}
              </span>
            </Button>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-4 sm:p-6">
          <div className="mx-auto w-full max-w-7xl">
            <SystemBulaCatalog />
          </div>
        </main>
      </div>
    </div>
  );
}
