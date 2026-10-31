import { Search } from "lucide-react";
import { type ReactElement, useId } from "react";

import type { RetrievalMode } from "@/api/chat";
import { ActionHint } from "@/components/ui/action-hint";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { isRetrievalMode, RETRIEVAL_MODES } from "@/lib/retrieval-mode";
import { cn } from "@/lib/utils";

interface ModeSelectorProps {
  value: RetrievalMode;
  isDisabled: boolean;
  onChange: (mode: RetrievalMode) => void;
  variant?: "compact" | "icon";
  isSidebar?: boolean;
}

export function ModeSelector({
  value,
  isDisabled,
  onChange,
  variant = "compact",
  isSidebar = true,
}: ModeSelectorProps): ReactElement {
  const descriptionId = useId();
  return (
    <Select
      value={value}
      disabled={isDisabled}
      onValueChange={(mode) => {
        if (isRetrievalMode(mode)) onChange(mode);
      }}
    >
      <ActionHint
        side={variant === "icon" ? "right" : "bottom"}
        label={`Modo de busca: ${RETRIEVAL_MODES[value].label}`}
      >
        <SelectTrigger
          aria-label="Modo de busca"
          aria-describedby={descriptionId}
          className={cn(
            "gap-2 rounded-lg border-transparent bg-transparent shadow-none",
            isSidebar ? "text-sidebar-foreground hover:bg-sidebar-accent" : "hover:bg-muted",
            variant === "icon"
              ? "w-11 justify-center px-0 data-[size=default]:h-11 [&>svg:last-child]:hidden"
              : "w-auto shrink-0 gap-1.5 px-2"
          )}
        >
          <Search aria-hidden="true" className="h-4 w-4" />
          <SelectValue>
            <span className={variant === "icon" ? "sr-only" : "sr-only sm:not-sr-only"}>
              {RETRIEVAL_MODES[value].label}
            </span>
          </SelectValue>
        </SelectTrigger>
      </ActionHint>
      <p id={descriptionId} className="sr-only">
        {RETRIEVAL_MODES[value].description}
      </p>
      <SelectContent
        className={cn(
          "w-80 max-w-[calc(100vw-2rem)]",
          isSidebar && "border-sidebar-border bg-sidebar text-sidebar-foreground"
        )}
      >
        {Object.entries(RETRIEVAL_MODES).map(([mode, option]) => (
          <SelectItem
            key={mode}
            value={mode}
            textValue={option.label}
            aria-labelledby={`${descriptionId}-${mode}-label`}
            aria-describedby={`${descriptionId}-${mode}`}
            className={cn(
              "cursor-pointer py-2.5",
              isSidebar && "focus:bg-sidebar-accent focus:text-sidebar-foreground"
            )}
          >
            <span className="flex flex-col items-start gap-1">
              <span id={`${descriptionId}-${mode}-label`} className="font-medium">
                {option.label}
              </span>
              <span
                id={`${descriptionId}-${mode}`}
                className={cn(
                  "text-xs leading-relaxed",
                  isSidebar ? "text-sidebar-foreground/65" : "text-muted-foreground"
                )}
              >
                {option.description}
              </span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
