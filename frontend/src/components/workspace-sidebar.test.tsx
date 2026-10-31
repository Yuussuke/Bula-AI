import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeAll, describe, expect, it } from "vitest";

import { UserInitialsAvatar } from "@/components/user-initials-avatar";
import { WorkspaceSidebar } from "@/components/workspace-sidebar";
import { useAuthStore } from "@/store/auth";

beforeAll(() => {
  Object.defineProperties(HTMLElement.prototype, {
    setPointerCapture: { configurable: true, value: () => undefined },
    hasPointerCapture: { configurable: true, value: () => false },
  });
});

function renderSidebar(): ReturnType<typeof render> {
  return render(
    <MemoryRouter>
      <WorkspaceSidebar shortcuts={null}>
        <p>Conversas</p>
      </WorkspaceSidebar>
    </MemoryRouter>
  );
}

describe("sidebar interaction", () => {
  it("accelerates a continuous drag without collapsing before release", () => {
    renderSidebar();
    const handle = screen.getByRole("button", { name: "Ajustar barra lateral" });
    const sidebar = screen.getByRole("complementary");
    fireEvent.pointerDown(handle, { button: 0, clientX: 288, pointerId: 1 });
    fireEvent.pointerMove(handle, { clientX: 248, pointerId: 1 });
    const gentleWidth = Number.parseFloat(sidebar.style.width);
    fireEvent.pointerMove(handle, { clientX: 208, pointerId: 1 });
    const middleWidth = Number.parseFloat(sidebar.style.width);
    fireEvent.pointerMove(handle, { clientX: 168, pointerId: 1 });
    const laterWidth = Number.parseFloat(sidebar.style.width);
    expect(288 - gentleWidth).toBeLessThan(40);
    expect(middleWidth - laterWidth).toBeGreaterThan(gentleWidth - middleWidth);
    expect(laterWidth).toBeGreaterThan(56);
    expect(handle).toHaveAttribute("aria-expanded", "true");
    fireEvent.pointerMove(handle, { clientX: 80, pointerId: 1 });
    fireEvent.pointerUp(handle, { clientX: 80, pointerId: 1 });
    expect(sidebar).toHaveStyle({ width: "56px" });
    expect(handle).toHaveAttribute("aria-expanded", "false");
  });

  it("toggles once on double click and keeps keyboard activation available", async () => {
    const user = userEvent.setup();
    renderSidebar();
    const handle = screen.getByRole("button", { name: "Ajustar barra lateral" });
    await user.dblClick(handle);
    expect(handle).toHaveAttribute("aria-expanded", "false");
    await user.dblClick(handle);
    expect(handle).toHaveAttribute("aria-expanded", "true");
    handle.focus();
    await user.keyboard("{Enter}");
    expect(handle).toHaveAttribute("aria-expanded", "false");
  });

  it("keeps the user's initials available in the rail after collapsing", async () => {
    useAuthStore.setState({
      user: { id: 1, name: "Ana Maria Costa", email: "user@example.test", role: "user" },
    });
    const user = userEvent.setup();
    renderSidebar();
    await user.click(screen.getByRole("button", { name: "Recolher barra lateral" }));
    expect(
      within(screen.getByRole("complementary")).getByRole("img", {
        name: "Ana Maria Costa",
      })
    ).toHaveTextContent("AC");
  });
});

describe("profile initials", () => {
  it.each([
    ["  Maria da Conceição  ", "MC"],
    ["João", "J"],
  ])("uses the first name and last surname for %s", (name, initials) => {
    render(<UserInitialsAvatar name={name} />);
    expect(screen.getByRole("img", { name: name.trim() })).toHaveTextContent(initials);
  });

  it("shows a neutral profile when no name is available", () => {
    render(<UserInitialsAvatar />);
    expect(screen.getByRole("img", { name: "Usuário" })).toBeVisible();
    expect(screen.getByRole("img")).not.toHaveTextContent("undefined");
  });
});
