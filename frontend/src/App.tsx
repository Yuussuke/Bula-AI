import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AuthView } from "@/components/auth-view";
import { DashboardView } from "@/components/dashboard-view";
import { bootstrapAuthSession } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

interface ProtectedRouteProps {
  authResolved: boolean;
  isAuthenticated: boolean;
}

function ProtectedRoute({ authResolved, isAuthenticated }: ProtectedRouteProps) {
  if (!authResolved) {
    return (
      <div className="bg-background text-foreground flex min-h-screen items-center justify-center">
        <p className="text-sm">Restoring your session...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  return <DashboardView />;
}

export default function App() {
  const authResolved = useAuthStore((state) => state.authResolved);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  useEffect(() => {
    void bootstrapAuthSession();
  }, []);

  return (
    <Routes>
      <Route
        path="/"
        element={<ProtectedRoute authResolved={authResolved} isAuthenticated={isAuthenticated} />}
      />
      <Route path="/auth" element={isAuthenticated ? <Navigate to="/" replace /> : <AuthView />} />
      <Route path="*" element={<Navigate to={isAuthenticated ? "/" : "/auth"} replace />} />
    </Routes>
  );
}
