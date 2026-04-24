import { useState } from "react";

import { AuthView } from "@/components/auth-view";
import { DashboardView } from "@/components/dashboard-view";

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return <AuthView onLogin={handleLogin} />;
  }

  return <DashboardView onLogout={handleLogout} />;
}
