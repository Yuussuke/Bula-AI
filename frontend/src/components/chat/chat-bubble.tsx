import { Bot, User } from "lucide-react";
import { lazy, memo, type ReactElement, Suspense, useCallback, useState } from "react";

import { ModeIndicator } from "@/components/chat/mode-indicator";
import { SourceChunks } from "@/components/chat/source-chunks";
import type { ChatTimelineMessage } from "@/components/chat/types";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const MessageMarkdown = memo(lazy(() => import("@/components/chat/message-markdown")));

interface ChatBubbleProps {
  message: ChatTimelineMessage;
}

export function ChatBubble({ message }: ChatBubbleProps): ReactElement {
  const isUserMessage = message.role === "user";
  const authorLabel = isUserMessage ? "Você" : "Bula AI";
  const isTransientMessage = message.deliveryStatus !== undefined;
  const [areSourcesOpen, setAreSourcesOpen] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState(1);

  const handleCitationClick = useCallback((citationNumber: number): void => {
    setSelectedCitation(citationNumber);
    setAreSourcesOpen(true);
  }, []);

  return (
    <article
      aria-label={`Mensagem de ${authorLabel}`}
      className={cn(
        "flex items-start gap-3",
        isUserMessage && "flex-row-reverse",
        isTransientMessage && "chat-message-enter"
      )}
    >
      <div
        aria-hidden="true"
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUserMessage ? "bg-primary text-primary-foreground" : "bg-primary/10 text-primary"
        )}
      >
        {isUserMessage ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div
        className={cn(
          "max-w-[85%] space-y-2 rounded-xl px-4 py-3 text-sm shadow-sm sm:max-w-[75%]",
          isUserMessage
            ? "bg-primary text-primary-foreground"
            : "bg-card border-border text-card-foreground border"
        )}
      >
        {isUserMessage ? (
          <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
        ) : (
          <Suspense
            fallback={
              <div role="status" aria-label="Formatando resposta" className="space-y-2 py-1">
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-5/6" />
              </div>
            }
          >
            <MessageMarkdown
              markdown={message.content}
              variant="answer"
              citationCount={message.sourceChunks.length}
              onCitationClick={handleCitationClick}
            />
          </Suspense>
        )}
        {message.deliveryStatus === "failed" ? (
          <p className="text-primary-foreground/85 text-right text-xs">Não foi possível enviar</p>
        ) : null}
        {!isUserMessage && <ModeIndicator mode={message.retrievalMode ?? null} />}
        {!isUserMessage && (
          <SourceChunks
            sourceChunks={message.sourceChunks}
            messageId={message.id}
            isOpen={areSourcesOpen}
            onOpenChange={setAreSourcesOpen}
            selectedCitation={selectedCitation}
          />
        )}
      </div>
    </article>
  );
}
