import { Send } from "lucide-react";
import {
  type FormEvent,
  type KeyboardEvent,
  type ReactElement,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
} from "react";

import type { ChatScope } from "@/api/chat";
import { MedicalWarning } from "@/components/medical-warning";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const MAX_INPUT_HEIGHT_PX = 144;

interface ChatComposerProps {
  value: string;
  isDisabled: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
  scope?: ChatScope;
}

export function ChatComposer({
  value,
  isDisabled,
  onChange,
  onSubmit,
  scope = "bula",
}: ChatComposerProps): ReactElement {
  const hasQuestion = value.trim().length > 0;
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const resizeInput = useCallback((): void => {
    const input = inputRef.current;
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, MAX_INPUT_HEIGHT_PX)}px`;
    input.style.overflowY = input.scrollHeight > input.clientHeight ? "auto" : "hidden";
  }, []);

  useLayoutEffect(resizeInput, [value, resizeInput]);
  useEffect(() => {
    window.addEventListener("resize", resizeInput);
    return () => window.removeEventListener("resize", resizeInput);
  }, [resizeInput]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (!hasQuestion || isDisabled) {
      return;
    }

    onSubmit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing || isDisabled) {
      return;
    }

    event.preventDefault();
    if (!hasQuestion) return;
    event.currentTarget.form?.requestSubmit();
  };

  return (
    <form onSubmit={handleSubmit} className="bg-background shrink-0 px-3 pt-2 pb-3 sm:px-6 sm:pb-4">
      <div className="mx-auto w-full max-w-3xl">
        <label htmlFor="chat-question" className="sr-only">
          {scope === "cross_bula"
            ? "Digite sua pergunta sobre um medicamento"
            : "Digite sua pergunta sobre a bula"}
        </label>
        <MedicalWarning />
        <div className="border-input bg-card focus-within:border-primary/50 flex items-end gap-2 rounded-2xl border p-2 shadow-xs sm:gap-3">
          <Textarea
            ref={inputRef}
            id="chat-question"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isDisabled}
            rows={1}
            placeholder={
              scope === "cross_bula"
                ? "Pergunte sobre um medicamento…"
                : "Pergunte sobre esta bula…"
            }
            aria-describedby="chat-question-help"
            className="[&::-webkit-scrollbar-thumb]:bg-border field-sizing-fixed max-h-36 min-h-11 resize-none [scrollbar-width:thin] overflow-y-hidden border-0 bg-transparent shadow-none focus-visible:ring-0 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-button]:hidden [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-track]:bg-transparent"
          />
          <Button
            type="submit"
            disabled={!hasQuestion || isDisabled}
            aria-label="Enviar pergunta"
            title="Enviar (Enter)"
            className="h-11 shrink-0 gap-2 rounded-xl px-3 sm:px-4"
          >
            <Send aria-hidden="true" className="h-4 w-4" />
            <span className="hidden sm:inline">Enviar</span>
          </Button>
        </div>
        <p id="chat-question-help" className="sr-only">
          Enter envia. Shift + Enter cria uma nova linha.
        </p>
      </div>
    </form>
  );
}
