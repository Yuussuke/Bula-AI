import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AssistantAvatar } from "@/components/assistant-avatar";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("assistant avatar interaction", () => {
  it("keeps pouring on hover while the click pulse starts and finishes", async () => {
    render(<AssistantAvatar />);
    const avatar = screen.getByRole("button", { name: "Animar assistente Bula AI" });
    const illustration = avatar.querySelector("svg");
    fireEvent.pointerEnter(avatar, { pointerType: "mouse" });
    fireEvent.click(avatar);
    expect(avatar).toHaveAttribute("data-pouring");
    expect(avatar).toHaveAttribute("data-pulsing");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(700);
    });
    expect(avatar).not.toHaveAttribute("data-pulsing");
    expect(avatar).toHaveAttribute("data-pouring");
    expect(avatar.querySelector("svg")).toBe(illustration);
    fireEvent.pointerLeave(avatar);
    expect(avatar).not.toHaveAttribute("data-pouring");
  });

  it("runs a complete touch interaction on the same illustration", async () => {
    render(<AssistantAvatar />);
    const avatar = screen.getByRole("button", { name: "Animar assistente Bula AI" });
    const illustration = avatar.querySelector("svg");
    fireEvent.pointerEnter(avatar, { pointerType: "touch" });
    expect(avatar).not.toHaveAttribute("data-pouring");
    fireEvent.pointerUp(avatar, { pointerType: "touch" });
    fireEvent.click(avatar);
    expect(avatar).toHaveAttribute("data-pouring");
    expect(avatar).toHaveAttribute("data-pulsing");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(700);
    });
    expect(avatar).not.toHaveAttribute("data-pulsing");
    expect(avatar).toHaveAttribute("data-pouring");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1200);
    });
    expect(avatar).not.toHaveAttribute("data-pouring");
    expect(avatar.querySelector("svg")).toBe(illustration);
  });
});
