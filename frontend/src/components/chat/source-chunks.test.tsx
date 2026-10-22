import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { SourceChunks } from "@/components/chat/source-chunks";

describe("SourceChunks", () => {
  it("keeps document attribution and canonical links attached to each numbered source", async () => {
    const user = userEvent.setup();
    render(
      <SourceChunks
        sourceChunks={[
          {
            chunk_id: "a",
            bula_id: "one",
            drug_name: "Produto A",
            manufacturer: "Fabricante A",
            presentation: "gotas",
            strength: "50 mg/mL",
            source_url: "https://consultas.anvisa.gov.br/a.pdf",
            section_title: "Advertências",
            chunk_text: "Texto A.",
            relevance_score: 0.5,
          },
          {
            chunk_id: "b",
            bula_id: "two",
            drug_name: "Produto B",
            manufacturer: "Fabricante B",
            presentation: "comprimidos",
            source_url: "javascript:alert(1)",
            section_title: "Advertências",
            chunk_text: "Texto B.",
            relevance_score: 0.4,
          },
        ]}
      />
    );
    await user.click(screen.getByRole("button", { name: "Ver 2 fontes na bula" }));
    expect(screen.getByText("Produto A")).toBeInTheDocument();
    expect(screen.getByText("Produto B")).toBeInTheDocument();
    expect(screen.getByText(/Fabricante A · gotas · 50 mg\/mL/)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Abrir fonte original" })).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Abrir fonte original" })).toHaveAttribute(
      "href",
      "https://consultas.anvisa.gov.br/a.pdf"
    );
  });
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
