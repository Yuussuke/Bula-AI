import { queryClient } from "@/lib/queryClient";
import { type AuthUser,useAuthStore } from "@/store/auth";

const envVariables = import.meta.env as Record<string, unknown>;
const apiBaseUrlFromEnv = envVariables.VITE_API_BASE_URL;
const API_BASE_URL =
  typeof apiBaseUrlFromEnv === "string" && apiBaseUrlFromEnv.length > 0
    ? apiBaseUrlFromEnv
    : "http://localhost:8000";
const AUTH_PREFIX = "/api/v1/auth";

interface AuthToken {
  access_token: string;
  token_type: string;
}

interface AuthPayload {
  token: AuthToken;
  user: AuthUser;
}

interface ApiErrorPayload {
  detail?: string;
}

interface AuthFetchOptions extends RequestInit {
  retryOnAuthError?: boolean;
}

export class SessionExpiredError extends Error {
  constructor(message = "Session expired. Please sign in again.") {
    super(message);
    this.name = "SessionExpiredError";
  }
}

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as ApiErrorPayload;
    if (typeof body.detail === "string" && body.detail.length > 0) {
      return body.detail;
    }
  } catch {
    // Fall back to status text.
  }

  return `Request failed with status ${response.status}`;
}

function clearAuthAndCache(): void {
  const authState = useAuthStore.getState();
  authState.clearAuth();
  queryClient.clear();
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshResponse = await fetch(`${API_BASE_URL}${AUTH_PREFIX}/refresh`, {
    method: "POST",
    credentials: "include",
  });

  if (!refreshResponse.ok) {
    return null;
  }

  const refreshPayload = (await refreshResponse.json()) as AuthToken;
  return refreshPayload.access_token;
}

export async function authFetch(path: string, init: AuthFetchOptions = {}): Promise<Response> {
  const authState = useAuthStore.getState();
  const shouldRetryOnAuthError = init.retryOnAuthError ?? true;

  const requestHeaders = new Headers(init.headers);
  if (authState.accessToken) {
    requestHeaders.set("Authorization", `Bearer ${authState.accessToken}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: requestHeaders,
    credentials: "include",
  });

  if (response.status !== 401) {
    return response;
  }

  if (!shouldRetryOnAuthError) {
    clearAuthAndCache();
    throw new SessionExpiredError();
  }

  const refreshedToken = await refreshAccessToken();
  if (!refreshedToken) {
    clearAuthAndCache();
    throw new SessionExpiredError();
  }

  authState.setAuth({ accessToken: refreshedToken });

  const retryHeaders = new Headers(init.headers);
  retryHeaders.set("Authorization", `Bearer ${refreshedToken}`);

  const retryResponse = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: retryHeaders,
    credentials: "include",
  });

  if (retryResponse.status === 401) {
    clearAuthAndCache();
    throw new SessionExpiredError();
  }

  return retryResponse;
}

async function requestJson<T>(path: string, init?: AuthFetchOptions): Promise<T> {
  const response = await authFetch(path, init);
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return (await response.json()) as T;
}

export interface RegisterRequest {
  email: string;
  full_name: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export async function registerRequest(payload: RegisterRequest): Promise<AuthPayload> {
  return requestJson<AuthPayload>(`${AUTH_PREFIX}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function loginRequest(payload: LoginRequest): Promise<AuthPayload> {
  return requestJson<AuthPayload>(`${AUTH_PREFIX}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function meRequest(): Promise<AuthUser> {
  return requestJson<AuthUser>(`${AUTH_PREFIX}/me`, {
    method: "GET",
  });
}

export async function logoutRequest(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${AUTH_PREFIX}/logout`, {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok && response.status !== 401) {
    throw new Error(await parseErrorMessage(response));
  }
}

export async function bootstrapAuthSession(): Promise<void> {
  const authState = useAuthStore.getState();
  authState.setAuthResolved(false);

  try {
    const refreshedToken = await refreshAccessToken();
    if (!refreshedToken) {
      authState.clearAuth();
      return;
    }

    authState.setAuth({ accessToken: refreshedToken });
    const user = await meRequest();
    authState.setAuth({ accessToken: refreshedToken, user });
  } catch {
    clearAuthAndCache();
  } finally {
    useAuthStore.getState().setAuthResolved(true);
  }
}

export function handleAuthLoss(): void {
  clearAuthAndCache();
}
