import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CatalogFilters } from "@/components/bulas/catalog-filters";

describe("catalog audience filter", () => {
  it("changes audience without introducing a second search or ordering control", () => {
    const onChange = vi.fn();
    render(<CatalogFilters audience="all" onChange={onChange} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "patient" } });
    expect(onChange).toHaveBeenCalledExactlyOnceWith("patient");
    expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
    expect(screen.getAllByRole("combobox")).toHaveLength(1);
  });

  it("reflects the audience restored by navigation", () => {
    const onChange = vi.fn();
    const { rerender } = render(<CatalogFilters audience="patient" onChange={onChange} />);
    rerender(<CatalogFilters audience="professional" onChange={onChange} />);
    expect(screen.getByRole("combobox")).toHaveValue("professional");
    expect(onChange).not.toHaveBeenCalled();
  });
});
