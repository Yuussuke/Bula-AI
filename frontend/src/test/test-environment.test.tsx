import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("frontend test environment", () => {
  it("renders React content with accessible DOM matchers", () => {
    render(<button type="button">Test environment ready</button>);

    expect(screen.getByRole("button", { name: "Test environment ready" })).toBeInTheDocument();
  });
});
