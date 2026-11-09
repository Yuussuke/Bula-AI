import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChatMessageList } from "@/components/chat/chat-message-list";
import type { ChatTimelineMessage } from "@/components/chat/types";

describe("conversation scrolling", () => {
  it("keeps the reply avatar mounted while the loading indicator becomes an answer", async () => {
    const question: ChatTimelineMessage = {
      id: "question",
      role: "user",
      content: "Minha pergunta",
      sourceChunks: [],
    };
    const { rerender } = render(<ChatMessageList messages={[question]} isResponding />);
    const pendingRow = screen.getByText("Bula AI está preparando a resposta…").closest("article");
    const avatar = pendingRow?.querySelector(".assistant-avatar svg");
    expect(avatar).not.toBeNull();
    rerender(
      <ChatMessageList
        messages={[
          question,
          { id: "reply", role: "assistant", content: "Resposta concluída.", sourceChunks: [] },
        ]}
        isResponding={false}
      />
    );
    expect(await screen.findByText("Resposta concluída.")).toBeInTheDocument();
    const completedRow = screen.getByRole("article", { name: "Mensagem de Bula AI" });
    expect(completedRow.querySelector(".assistant-avatar svg")).toBe(avatar);
    expect(screen.queryByText("Bula AI está preparando a resposta…")).not.toBeInTheDocument();
    await waitFor(() =>
      expect(completedRow.querySelector(".assistant-avatar")).not.toHaveAttribute("data-loading")
    );
  });
  it("preserves reading position and offers an explicit return to the latest message", async () => {
    const scrollTo = vi.fn();
    const messages: ChatTimelineMessage[] = [
      { id: "one", role: "user", content: "Pergunta anterior", sourceChunks: [] },
    ];
    const { rerender } = render(<ChatMessageList messages={messages} isResponding={false} />);
    const log = screen.getByRole("log");
    Object.defineProperties(log, {
      scrollHeight: { configurable: true, value: 2400 },
      clientHeight: { configurable: true, value: 400 },
      scrollTop: { configurable: true, value: 0 },
      scrollTo: { configurable: true, value: scrollTo },
    });
    fireEvent.scroll(log);
    const returnButton = screen.getByRole("button", { name: "Ir para a última mensagem" });
    rerender(
      <ChatMessageList
        messages={[
          ...messages,
          { id: "two", role: "assistant", content: "Nova resposta", sourceChunks: [] },
        ]}
        isResponding={false}
      />
    );
    expect(scrollTo).not.toHaveBeenCalled();
    await userEvent.setup().click(returnButton);
    expect(scrollTo).toHaveBeenCalledWith({ top: 2400, behavior: "auto" });
    expect(
      screen.queryByRole("button", { name: "Ir para a última mensagem" })
    ).not.toBeInTheDocument();
  });
});
