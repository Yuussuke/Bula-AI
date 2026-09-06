import { Bot, Loader2 } from "lucide-react";
import { type ReactElement, useEffect, useRef } from "react";

import { ChatBubble } from "@/components/chat/chat-bubble";
import type { ChatTimelineMessage } from "@/components/chat/types";

interface ChatMessageListProps {
  messages: ChatTimelineMessage[];
  isResponding: boolean;
}

export function ChatMessageList({ messages, isResponding }: ChatMessageListProps): ReactElement {
  const conversationEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [isResponding, messages.length]);

  return (
    <div
      role="log"
      aria-label="Histórico da conversa"
      aria-busy={isResponding}
      aria-live="polite"
      className="flex-1 space-y-5 overflow-y-auto px-4 py-5 sm:px-6"
    >
      {messages.length === 0 && !isResponding ? (
        <div className="text-muted-foreground mx-auto flex max-w-md flex-col items-center py-12 text-center">
          <div className="bg-primary/10 text-primary mb-4 flex h-12 w-12 items-center justify-center rounded-full">
            <Bot aria-hidden="true" className="h-6 w-6" />
          </div>
          <h2 className="text-foreground text-base font-semibold">Converse sobre esta bula</h2>
          <p className="mt-2 text-sm leading-relaxed">
            Faça uma pergunta sobre indicações, modo de uso, contraindicações ou outras informações
            presentes no documento.
          </p>
        </div>
      ) : null}

      {messages.map((message) => (
        <ChatBubble key={message.id} message={message} />
      ))}

      {isResponding ? (
        <div role="status" className="flex items-center gap-3">
          <div className="bg-primary/10 text-primary flex h-8 w-8 items-center justify-center rounded-full">
            <Bot aria-hidden="true" className="h-4 w-4" />
          </div>
          <div className="bg-card border-border flex items-center gap-2 rounded-xl border px-4 py-3 text-sm">
            <Loader2 aria-hidden="true" className="text-primary h-4 w-4 animate-spin" />
            <span>Bula AI está preparando a resposta…</span>
          </div>
        </div>
      ) : null}

      <div ref={conversationEndRef} aria-hidden="true" />
    </div>
  );
}
