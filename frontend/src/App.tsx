import { lazy, type ReactElement, Suspense, useEffect } from "react";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { AuthView } from "@/components/auth-view";
import { BulaCatalog } from "@/components/bulas/bula-catalog";
import { UserBulaSection } from "@/components/bulas/user-bula-section";
import { DashboardView } from "@/components/dashboard-view";
import { bootstrapAuthSession } from "@/lib/api";
import { getPostAuthPath } from "@/lib/auth-navigation";
import { ChatPage } from "@/pages/chat-page";
import { HomePage } from "@/pages/home-page";
import { useAuthStore } from "@/store/auth";

const SharedBulasPage = lazy(() =>
  import("@/pages/shared-bulas-page").then((module) => ({ default: module.SharedBulasPage }))
);
const CurationUsersPage = lazy(() =>
  import("@/pages/curation-users-page").then((module) => ({ default: module.CurationUsersPage }))
);

interface ProtectedRouteProps {
  authResolved: boolean;
  isAuthenticated: boolean;
}

function ProtectedRoute({ authResolved, isAuthenticated }: ProtectedRouteProps): ReactElement {
  const location = useLocation();

  if (!authResolved) {
    return (
      <div className="bg-background text-foreground flex min-h-screen items-center justify-center">
        <p className="text-sm">Restoring your session...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    const returnTo = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to="/auth" replace state={{ returnTo }} />;
  }

  return <Outlet />;
}

function AuthRoute({ authResolved, isAuthenticated }: ProtectedRouteProps): ReactElement {
  const location = useLocation();

  if (!authResolved) {
    return (
      <div className="bg-background text-foreground flex min-h-screen items-center justify-center">
        <p className="text-sm">Restoring your session...</p>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to={getPostAuthPath(location.state)} replace />;
  }

  return <AuthView />;
}

export default function App(): ReactElement {
  const location = useLocation();
  const authResolved = useAuthStore((state) => state.authResolved);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  useEffect(() => {
    void bootstrapAuthSession();
  }, []);

  return (
    <div key={location.pathname} className="route-transition">
      <Routes location={location}>
        <Route
          element={<ProtectedRoute authResolved={authResolved} isAuthenticated={isAuthenticated} />}
        >
          <Route element={<DashboardView />}>
            <Route index element={<HomePage />} />
            <Route path="/catalogo" element={<BulaCatalog />} />
            <Route path="/minhas-bulas" element={<UserBulaSection />} />
            <Route
              element={
                <Suspense fallback={<p role="status">Carregando…</p>}>
                  <Outlet />
                </Suspense>
              }
            >
              <Route path="/compartilhadas" element={<SharedBulasPage />} />
              <Route path="/curadoria" element={<SharedBulasPage review />} />
              <Route path="/administracao/usuarios" element={<CurationUsersPage />} />
            </Route>
          </Route>
          <Route path="/chat" element={<ChatPage scope="cross_bula" />} />
          <Route path="/bulas/:bulaId/chat" element={<ChatPage />} />
        </Route>
        <Route
          path="/auth"
          element={<AuthRoute authResolved={authResolved} isAuthenticated={isAuthenticated} />}
        />
        <Route path="*" element={<Navigate to={isAuthenticated ? "/" : "/auth"} replace />} />
      </Routes>
    </div>
  );
}
