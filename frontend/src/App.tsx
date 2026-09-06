import { type ReactElement, useEffect } from "react";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { AuthView } from "@/components/auth-view";
import { DashboardView } from "@/components/dashboard-view";
import { bootstrapAuthSession } from "@/lib/api";
import { getPostAuthPath } from "@/lib/auth-navigation";
import { ChatPage } from "@/pages/chat-page";
import { useAuthStore } from "@/store/auth";

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
          <Route path="/" element={<DashboardView />} />
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
