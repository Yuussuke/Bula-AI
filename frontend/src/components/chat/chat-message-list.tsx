import { ArrowDown, Loader2 } from "lucide-react";
import { type ReactElement, useEffect, useRef, useState } from "react";

import type { ChatScope } from "@/api/chat";
import { BrandLogo } from "@/components/brand-logo";
import { ChatBubble } from "@/components/chat/chat-bubble";
import type { ChatTimelineMessage } from "@/components/chat/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ChatMessageListProps {
  messages: ChatTimelineMessage[];
  isResponding: boolean;
  scope?: ChatScope;
  onSuggestionSelected?: (question: string) => void;
}

export function ChatMessageList({
  messages,
  isResponding,
  scope = "bula",
  onSuggestionSelected,
}: ChatMessageListProps): ReactElement {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const shouldFollowRef = useRef(true);
  const [isAtBottom, setIsAtBottom] = useState(true);

  const scrollToLatest = (): void => {
    const container = scrollContainerRef.current;
    if (!container) return;
    shouldFollowRef.current = true;
    container.scrollTo?.({ top: container.scrollHeight, behavior: "auto" });
    setIsAtBottom(true);
  };

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    if (messages.at(-1)?.role === "user") shouldFollowRef.current = true;
    if (shouldFollowRef.current)
      container.scrollTo?.({ top: container.scrollHeight, behavior: "auto" });
  }, [isResponding, messages]);

  // Lazy Markdown can change the height after the message arrives.
  useEffect(() => {
    if (typeof ResizeObserver === "undefined" || !contentRef.current) return;
    const observer = new ResizeObserver(() => {
      const container = scrollContainerRef.current;
      if (container && shouldFollowRef.current)
        container.scrollTo?.({ top: container.scrollHeight, behavior: "auto" });
    });
    observer.observe(contentRef.current);
    return () => observer.disconnect();
  }, []);

  const suggestions =
    scope === "cross_bula"
      ? [
          {
            label: "Conservação",
            question: "Como devo conservar [medicamento]?",
          },
          {
            label: "Cuidados de uso",
            question: "Quais cuidados devo ter ao usar [medicamento]?",
          },
          {
            label: "Efeitos indesejáveis",
            question: "Quais efeitos indesejáveis [medicamento] pode causar?",
          },
        ]
      : [
          { label: "Para que serve?", question: "Para que serve este medicamento?" },
          {
            label: "Cuidados de uso",
            question: "Quais cuidados devo ter ao usar este medicamento?",
          },
          { label: "Como conservar?", question: "Como devo conservar este medicamento?" },
        ];

  return (
    <div className="relative min-h-0 flex-1">
      <div
        ref={scrollContainerRef}
        role="log"
        aria-label="Histórico da conversa"
        aria-busy={isResponding}
        aria-live="polite"
        className="clean-scroll h-full overflow-y-auto overscroll-contain px-4 py-5 sm:px-6"
        onScroll={(event) => {
          const container = event.currentTarget;
          const nearBottom =
            container.scrollHeight - container.scrollTop - container.clientHeight < 80;
          shouldFollowRef.current = nearBottom;
          setIsAtBottom(nearBottom);
        }}
      >
        <div
          ref={contentRef}
          className={cn(
            "mx-auto w-full max-w-3xl space-y-5",
            messages.length === 0 && !isResponding && "flex min-h-full flex-col justify-center"
          )}
        >
          {messages.length === 0 && !isResponding ? (
            <div className="text-muted-foreground mx-auto flex max-w-md flex-col items-center py-12 text-center">
              <div className="bg-primary/10 text-primary mb-4 flex h-12 w-12 items-center justify-center rounded-full">
                <BrandLogo className="h-7 w-9" />
              </div>
              <h2 className="text-foreground text-base font-semibold">
                {scope === "cross_bula"
                  ? "Consulte as bulas do catálogo"
                  : "Converse sobre esta bula"}
              </h2>
              <p className="mt-2 text-sm leading-relaxed">
                {scope === "cross_bula"
                  ? "Diga o nome do medicamento e sua dúvida. As respostas usam as bulas disponíveis no catálogo."
                  : "Pergunte sobre indicações, cuidados, conservação e outras informações do documento selecionado."}
              </p>
              {onSuggestionSelected ? (
                <>
                  <div className="mt-5 flex flex-wrap justify-center gap-2">
                    {suggestions.map((suggestion) => (
                      <Button
                        key={suggestion.label}
                        size="sm"
                        variant="outline"
                        onClick={() => onSuggestionSelected(suggestion.question)}
                      >
                        {suggestion.label}
                      </Button>
                    ))}
                  </div>
                  <p className="mt-3 text-xs">
                    {scope === "cross_bula"
                      ? "Escolha um tema, complete o medicamento e revise antes de enviar."
                      : "Uma sugestão apenas preenche a pergunta. Você pode editá-la antes de enviar."}
                  </p>
                </>
              ) : null}
            </div>
          ) : null}

          {messages.map((message) => (
            <ChatBubble key={message.id} message={message} />
          ))}

          {isResponding ? (
            <div role="status" className="flex items-center gap-3">
              <div className="bg-primary/10 text-primary flex h-8 w-8 items-center justify-center rounded-full">
                <BrandLogo className="h-5 w-6" />
              </div>
              <div className="bg-card border-border flex items-center gap-2 rounded-xl border px-4 py-3 text-sm">
                <Loader2 aria-hidden="true" className="text-primary h-4 w-4 animate-spin" />
                <span>Bula AI está preparando a resposta…</span>
              </div>
            </div>
          ) : null}
        </div>
      </div>
      {!isAtBottom ? (
        <Button
          size="sm"
          variant="secondary"
          className="absolute right-4 bottom-3 shadow-md"
          onClick={scrollToLatest}
        >
          <ArrowDown aria-hidden="true" className="mr-2 h-4 w-4" />
          Ir para a última mensagem
        </Button>
      ) : null}
    </div>
  );
}
