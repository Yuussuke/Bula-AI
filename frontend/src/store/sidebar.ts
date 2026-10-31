import { create } from "zustand";

interface SidebarState {
  isCollapsed: boolean;
  setCollapsed: (isCollapsed: boolean) => void;
}

// Shared across routes; authentication and conversation data stay in their own stores.
export const useSidebarStore = create<SidebarState>((set) => ({
  isCollapsed: false,
  setCollapsed: (isCollapsed) => set({ isCollapsed }),
}));
