import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatBubble } from "@/components/chat/chat-bubble";

describe("ChatBubble citations", () => {
  const scrollIntoViewMock = vi.fn();

  beforeEach(() => {
    Object.defineProperty(Element.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollIntoViewMock,
    });
  });

  afterEach(() => {
    Reflect.deleteProperty(Element.prototype, "scrollIntoView");
    vi.restoreAllMocks();
  });

  it("opens the cited sources and moves focus to the selected chunk", async () => {
    const user = userEvent.setup();
    render(
      <ChatBubble
        message={{
          id: "assistant-1",
          role: "assistant",
          content: "Use conforme a orientação [1].",
          sourceChunks: [
            {
              section_title: "POSOLOGIA",
              chunk_text: "## POSOLOGIA\nTomar conforme orientação médica.",
              relevance_score: 0.95,
            },
          ],
        }}
      />
    );

    const citationLink = await screen.findByRole(
      "link",
      { name: "Ir para a fonte 1" },
      { timeout: 5_000 }
    );
    await user.click(citationLink);

    await waitFor(
      () => {
        const citedChunk = document.getElementById("chat-message-assistant-1-source-1");
        expect(screen.getByRole("button", { name: "Ver 1 fonte na bula" })).toHaveAttribute(
          "data-state",
          "open"
        );
        expect(citedChunk).toHaveFocus();
        expect(scrollIntoViewMock).toHaveBeenCalledWith({
          behavior: "smooth",
          block: "center",
        });
      },
      { timeout: 5_000 }
    );
  }, 10_000);
});
