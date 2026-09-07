import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

class ResizeObserverMock implements ResizeObserver {
  readonly observedElements: Element[] = [];

  disconnect(): void {
    this.observedElements.length = 0;
  }

  observe(target: Element): void {
    this.observedElements.push(target);
  }

  unobserve(target: Element): void {
    const targetIndex = this.observedElements.indexOf(target);
    if (targetIndex >= 0) {
      this.observedElements.splice(targetIndex, 1);
    }
  }
}

vi.stubGlobal("ResizeObserver", ResizeObserverMock);

afterEach(() => {
  cleanup();
});
