import { createContext } from "react";

interface WorkspaceSidebarTargets {
  content: HTMLDivElement | null;
  footer: HTMLDivElement | null;
  rail: HTMLDivElement | null;
  registerStartNewSession: (action: () => void) => () => void;
  setCatalogReturnTo: (path: string | null) => void;
}

// Route content fills these slots without replacing the persistent navigation.
export const WorkspaceSidebarContext = createContext<WorkspaceSidebarTargets | null>(null);
