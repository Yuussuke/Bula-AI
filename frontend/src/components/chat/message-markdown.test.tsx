import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import MessageMarkdown from "@/components/chat/message-markdown";

describe("MessageMarkdown", () => {
  it("links grouped citations without renumbering or linking unknown IDs", async () => {
    const user = userEvent.setup();
    const onCitationClick = vi.fn();
    render(
      <MessageMarkdown
        markdown="Fontes [2, 1]. Grupo inválido [1,9]."
        variant="answer"
        citationCount={2}
        onCitationClick={onCitationClick}
      />
    );
    await user.click(screen.getByRole("link", { name: "Ir para a fonte 2" }));
    expect(onCitationClick).toHaveBeenCalledWith(2);
    expect(screen.getByRole("link", { name: "Ir para a fonte 1" })).toBeInTheDocument();
    expect(screen.getByText(/Grupo inválido \[1,9\]/)).toBeInTheDocument();
  });
  it("preserves visible spacing before bold text", () => {
    const { container } = render(
      <MessageMarkdown
        markdown="Isso indica que **pacientes com problemas no fígado** precisam de acompanhamento."
        variant="answer"
      />
    );

    expect(container).toHaveTextContent(
      "Isso indica que pacientes com problemas no fígado precisam de acompanhamento."
    );
    expect(container.textContent).toContain("que\u00a0pacientes");
  });

  it("turns valid numeric citations into interactive links", async () => {
    const user = userEvent.setup();
    const handleCitationClick = vi.fn();
    render(
      <MessageMarkdown
        markdown="A orientação está no trecho [1]. A referência [3] não existe."
        variant="answer"
        citationCount={2}
        onCitationClick={handleCitationClick}
      />
    );

    const citationLink = screen.getByRole("link", { name: "Ir para a fonte 1" });
    expect(citationLink.parentElement?.tagName).toBe("SUP");
    expect(citationLink.parentElement).not.toHaveClass("ml-0.5");
    expect(citationLink).not.toHaveClass("rounded");
    expect(citationLink.closest("p")).toHaveTextContent("trecho1.");
    expect(citationLink.parentElement?.previousSibling?.textContent).toMatch(/trecho$/);
    expect(citationLink.closest("p")).toHaveTextContent("referência [3]");

    await user.click(citationLink);

    expect(handleCitationClick).toHaveBeenCalledWith(1);
    expect(screen.getByText("[3]", { exact: false })).toBeInTheDocument();
  });
});
