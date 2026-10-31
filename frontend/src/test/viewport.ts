import { vi } from "vitest";

const listeners = new Set<() => void>();

export function setViewportWidth(width: number): void {
  Object.defineProperty(window, "innerWidth", { configurable: true, writable: true, value: width });
  listeners.forEach((listener) => listener());
}

export function installViewportMock(): void {
  listeners.clear();
  setViewportWidth(1280);
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: window.innerWidth <= Number(query.match(/\d+/)?.[0] ?? 0),
    media: query,
    addEventListener: (_name: string, listener: () => void) => listeners.add(listener),
    removeEventListener: (_name: string, listener: () => void) => listeners.delete(listener),
  }));
}
