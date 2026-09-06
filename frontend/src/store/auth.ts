import { create } from "zustand";

export interface AuthUser {
  id: number;
  email: string;
  name: string;
  role: "user" | "admin" | "reviewer";
}

interface SetAuthPayload {
  accessToken: string;
  user: AuthUser;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  authResolved: boolean;
  isAuthenticated: boolean;
  setAccessToken: (accessToken: string) => void;
  setAuth: (payload: SetAuthPayload) => void;
  clearAuth: () => void;
  setAuthResolved: (authResolved: boolean) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  authResolved: false,
  isAuthenticated: false,
  setAccessToken: (accessToken) => {
    const existingUser = get().user;
    set({
      accessToken,
      isAuthenticated: Boolean(accessToken && existingUser),
    });
  },
  setAuth: ({ accessToken, user }) => {
    set({
      accessToken,
      user,
      authResolved: true,
      isAuthenticated: Boolean(accessToken && user),
    });
  },
  clearAuth: () => {
    set({
      user: null,
      accessToken: null,
      authResolved: true,
      isAuthenticated: false,
    });
  },
  setAuthResolved: (authResolved: boolean) => {
    set({ authResolved });
  },
}));
