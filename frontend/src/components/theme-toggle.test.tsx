import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";

const storageKey = "bula-ai-theme-test";
const listeners = new Set<(event: MediaQueryListEvent) => void>();
let isSystemDark = false;
let originalStorage: PropertyDescriptor | undefined;

function changeSystemTheme(isDark: boolean): void {
  isSystemDark = isDark;
  const event = Object.assign(new Event("change"), {
    matches: isDark,
    media: "(prefers-color-scheme: dark)",
  });
  listeners.forEach((listener) => listener(event));
}

function renderToggle(): ReturnType<typeof render> {
  return render(
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem storageKey={storageKey}>
      <ThemeToggle />
    </ThemeProvider>
  );
}

beforeEach(() => {
  isSystemDark = false;
  listeners.clear();
  const values = new Map<string, string>();
  const storage: Storage = {
    get length(): number {
      return values.size;
    },
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => {
      values.set(key, value);
    },
    removeItem: (key) => {
      values.delete(key);
    },
    clear: () => {
      values.clear();
    },
    key: (index) => [...values.keys()][index] ?? null,
  };
  originalStorage = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: storage });
  document.documentElement.classList.remove("dark", "light");
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query: string): MediaQueryList => ({
      get matches(): boolean {
        return isSystemDark;
      },
      media: query,
      onchange: null,
      addListener: (listener) => {
        if (listener) listeners.add(listener);
      },
      removeListener: (listener) => {
        if (listener) listeners.delete(listener);
      },
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => true,
    })
  );
});

afterEach(() => {
  window.localStorage.removeItem(storageKey);
  document.documentElement.classList.remove("dark", "light");
  if (originalStorage) Object.defineProperty(globalThis, "localStorage", originalStorage);
  vi.restoreAllMocks();
});

describe("theme shortcut", () => {
  it("follows system changes until the user explicitly selects a theme", async () => {
    renderToggle();
    expect(screen.getByRole("button", { name: "Ativar tema escuro" })).toBeVisible();
    act(() => changeSystemTheme(true));
    expect(await screen.findByRole("button", { name: "Ativar tema claro" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(document.documentElement).toHaveClass("dark");
    await userEvent.setup().click(screen.getByRole("button", { name: "Ativar tema claro" }));
    expect(document.documentElement).toHaveClass("light");
    act(() => changeSystemTheme(true));
    expect(document.documentElement).toHaveClass("light");
  });

  it("supports the keyboard and restores the chosen theme on a fresh mount", async () => {
    const user = userEvent.setup();
    const view = renderToggle();
    await user.tab();
    expect(screen.getByRole("button", { name: "Ativar tema escuro" })).toHaveFocus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(document.documentElement).toHaveClass("dark"));
    await waitFor(() => expect(window.localStorage.getItem(storageKey)).toBe("dark"));
    view.unmount();
    renderToggle();
    expect(screen.getByRole("button", { name: "Ativar tema claro" })).toBeVisible();
    expect(document.documentElement).toHaveClass("dark");
  });
});
