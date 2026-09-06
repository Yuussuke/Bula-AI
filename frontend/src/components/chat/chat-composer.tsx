import { Send } from "lucide-react";
import type { FormEvent, KeyboardEvent, ReactElement } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ChatComposerProps {
  value: string;
  isDisabled: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export function ChatComposer({
  value,
  isDisabled,
  onChange,
  onSubmit,
}: ChatComposerProps): ReactElement {
  const hasQuestion = value.trim().length > 0;

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (!hasQuestion || isDisabled) {
      return;
    }

    onSubmit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (
      event.key !== "Enter" ||
      event.shiftKey ||
      event.nativeEvent.isComposing ||
      !hasQuestion ||
      isDisabled
    ) {
      return;
    }

    event.preventDefault();
    event.currentTarget.form?.requestSubmit();
  };

  return (
    <form onSubmit={handleSubmit} className="border-border bg-card border-t p-4 sm:p-5">
      <label htmlFor="chat-question" className="sr-only">
        Digite sua pergunta sobre a bula
      </label>
      <div className="flex items-end gap-2 sm:gap-3">
        <Textarea
          id="chat-question"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isDisabled}
          rows={2}
          placeholder="Pergunte sobre esta bula…"
          aria-describedby="chat-question-help"
          className="max-h-40 min-h-12 resize-none"
        />
        <Button
          type="submit"
          disabled={!hasQuestion || isDisabled}
          aria-label="Enviar pergunta"
          className="h-12 shrink-0 gap-2 px-4 sm:px-5"
        >
          <Send aria-hidden="true" className="h-4 w-4" />
          <span className="hidden sm:inline">Enviar</span>
        </Button>
      </div>
      <p id="chat-question-help" className="text-muted-foreground mt-2 text-xs">
        Enter envia. Shift + Enter cria uma nova linha.
      </p>
    </form>
  );
}
