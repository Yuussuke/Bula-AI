import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { SourceChunks } from "@/components/chat/source-chunks";

describe("SourceChunks", () => {
  it("presents Markdown as readable headings, lists and tables", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <SourceChunks
        sourceChunks={[
          {
            section_title: "POSOLOGIA",
            chunk_text: [
              "## POSOLOGIA",
              "",
              "### Adultos",
              "",
              "- Tomar 1 comprimido de 500 mg.",
              "- Não exceder a dose indicada.",
              "",
              "| Peso | Dose |",
              "| --- | --- |",
              "| 40 kg | 500 mg |",
            ].join("\n"),
            relevance_score: 0.95,
          },
        ]}
      />
    );

    await user.click(screen.getByRole("button", { name: "Ver 1 fonte na bula" }));

    expect(screen.getAllByText("POSOLOGIA")).toHaveLength(1);
    expect(
      await screen.findByRole("heading", { name: "Adultos" }, { timeout: 5_000 })
    ).toBeInTheDocument();
    expect(screen.getByText("Tomar 1 comprimido de 500 mg.")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Peso" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "40 kg" })).toBeInTheDocument();
    expect(container).not.toHaveTextContent("##");
    expect(container).not.toHaveTextContent("| Peso | Dose |");
  }, 10_000);
});
