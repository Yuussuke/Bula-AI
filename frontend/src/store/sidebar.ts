import { create } from "zustand";

interface SidebarState {
  isCollapsed: boolean;
  setCollapsed: (isCollapsed: boolean) => void;
  expandedConversationGroups: string[];
  setExpandedConversationGroups: (groups: string[]) => void;
}

// Shared across routes; authentication and conversation data stay in their own stores.
export const useSidebarStore = create<SidebarState>((set) => ({
  isCollapsed: false,
  setCollapsed: (isCollapsed) => set({ isCollapsed }),
  expandedConversationGroups: ["pinned", "cross_bula", "bula"],
  setExpandedConversationGroups: (groups) => set({ expandedConversationGroups: groups }),
}));
