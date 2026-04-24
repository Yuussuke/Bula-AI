import { create } from "zustand";

export interface AuthUser {
  id: number;
  email: string;
  name: string;
}

interface SetAuthPayload {
  accessToken: string;
  user?: AuthUser;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  authResolved: boolean;
  isAuthenticated: boolean;
  setAuth: (payload: SetAuthPayload) => void;
  clearAuth: () => void;
  setAuthResolved: (authResolved: boolean) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  authResolved: false,
  isAuthenticated: false,
  setAuth: ({ accessToken, user }) => {
    const existingUser = get().user;
    const nextUser = user ?? existingUser;

    set({
      accessToken,
      user: nextUser,
      authResolved: true,
      isAuthenticated: Boolean(accessToken && nextUser),
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
