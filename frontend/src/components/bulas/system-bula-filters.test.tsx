import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SystemBulaFilters } from "@/components/bulas/system-bula-filters";

afterEach(() => vi.useRealTimers());

describe("dynamic catalog search", () => {
  it("waits for a typing pause, emits only the latest query and keeps input focus", async () => {
    vi.useFakeTimers();
    const onSearch = vi.fn();
    const { rerender } = render(
      <SystemBulaFilters searchTerm="" audience="all" sort="name_asc" onSearch={onSearch} />
    );
    const input = screen.getByRole("searchbox");
    input.focus();
    for (const value of ["d", "dipi", "dipirona"]) fireEvent.change(input, { target: { value } });
    await act(() => vi.advanceTimersByTime(349));
    expect(onSearch).not.toHaveBeenCalled();
    await act(() => vi.advanceTimersByTime(1));
    expect(onSearch).toHaveBeenCalledExactlyOnceWith("dipirona", "all", "name_asc");
    rerender(
      <SystemBulaFilters searchTerm="dipirona" audience="all" sort="name_asc" onSearch={onSearch} />
    );
    expect(input).toHaveFocus();
    fireEvent.change(input, { target: { value: "dipirona gotas" } });
    await act(() => vi.advanceTimersByTime(350));
    expect(onSearch).toHaveBeenLastCalledWith("dipirona gotas", "all", "name_asc");
  });

  it("applies form submission or a select change immediately and cancels the queued search", async () => {
    vi.useFakeTimers();
    const onSearch = vi.fn();
    render(<SystemBulaFilters searchTerm="" audience="all" sort="name_asc" onSearch={onSearch} />);
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "metformina" } });
    fireEvent.change(screen.getByRole("combobox", { name: "Filtrar por público da bula" }), {
      target: { value: "patient" },
    });
    expect(onSearch).toHaveBeenCalledExactlyOnceWith("metformina", "patient", "name_asc");
    await act(() => vi.advanceTimersByTime(500));
    expect(onSearch).toHaveBeenCalledTimes(1);
    fireEvent.submit(screen.getByRole("search"));
    expect(onSearch).toHaveBeenCalledTimes(2);
  });

  it("cancels a pending query on navigation and restores externally changed filters", async () => {
    vi.useFakeTimers();
    const onSearch = vi.fn();
    const { rerender, unmount } = render(
      <SystemBulaFilters searchTerm="" audience="all" sort="name_asc" onSearch={onSearch} />
    );
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "unfinished" } });
    rerender(
      <SystemBulaFilters
        searchTerm="amoxicilina"
        audience="patient"
        sort="name_desc"
        onSearch={onSearch}
      />
    );
    await act(() => vi.advanceTimersByTime(500));
    expect(onSearch).not.toHaveBeenCalled();
    expect(screen.getByRole("searchbox")).toHaveValue("amoxicilina");
    expect(screen.getByRole("combobox", { name: "Ordenar catálogo" })).toHaveValue("name_desc");
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "amoxicilina extra" } });
    unmount();
    await act(() => vi.advanceTimersByTime(500));
    expect(onSearch).not.toHaveBeenCalled();
  });
});
