import { act, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "@/App";
import { useAuthStore } from "@/store/auth";

const { bootstrapAuthSessionMock } = vi.hoisted(() => ({
  bootstrapAuthSessionMock: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/api", () => ({
  bootstrapAuthSession: bootstrapAuthSessionMock,
}));

vi.mock("@/components/auth-view", () => ({
  AuthView: () => <p>Authentication screen</p>,
}));

vi.mock("@/components/dashboard-view", () => ({
  DashboardView: () => <p>Dashboard screen</p>,
}));

vi.mock("@/pages/chat-page", () => ({
  ChatPage: () => <p>Chat screen</p>,
}));

function LocationProbe(): ReactElement {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}</output>;
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({
    user: null,
    accessToken: null,
    authResolved: true,
    isAuthenticated: false,
  });
});

describe("protected application routes", () => {
  it("redirects an unauthenticated chat visitor to the authentication page", async () => {
    render(
      <MemoryRouter initialEntries={["/bulas/bula-id/chat"]}>
        <App />
        <LocationProbe />
      </MemoryRouter>
    );

    expect(await screen.findByText("Authentication screen")).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("/auth");
    expect(screen.queryByText("Chat screen")).not.toBeInTheDocument();
    expect(bootstrapAuthSessionMock).toHaveBeenCalledOnce();
  });

  it("keeps the requested chat route while the refreshed user is loading", async () => {
    let resolveUserProfile: (() => void) | undefined;
    const userProfilePending = new Promise<void>((resolve) => {
      resolveUserProfile = resolve;
    });

    useAuthStore.setState({
      user: null,
      accessToken: null,
      authResolved: false,
      isAuthenticated: false,
    });
    bootstrapAuthSessionMock.mockImplementationOnce(async () => {
      const authState = useAuthStore.getState();
      authState.setAuthResolved(false);
      authState.setAccessToken("refreshed-access-token");
      await userProfilePending;
      authState.setAuth({
        accessToken: "refreshed-access-token",
        user: {
          id: 5,
          email: "admin@bulaai.com",
          name: "Administrador Bula AI",
          role: "admin",
        },
      });
    });

    render(
      <MemoryRouter initialEntries={["/bulas/bula-id/chat"]}>
        <App />
        <LocationProbe />
      </MemoryRouter>
    );

    expect(await screen.findByText("Restoring your session...")).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("/bulas/bula-id/chat");

    await act(async () => {
      resolveUserProfile?.();
      await userProfilePending;
    });

    const chatScreen = await screen.findByText("Chat screen");
    expect(chatScreen).toBeInTheDocument();
    expect(chatScreen.closest(".route-transition")).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("/bulas/bula-id/chat");
  });
});
