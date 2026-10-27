import { CircleHelp } from "lucide-react";
import { type ReactElement, useId } from "react";

import type { RetrievalMode } from "@/api/chat";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { isRetrievalMode, RETRIEVAL_MODES } from "@/lib/retrieval-mode";

interface ModeSelectorProps {
  value: RetrievalMode;
  isDisabled: boolean;
  onChange: (mode: RetrievalMode) => void;
}

export function ModeSelector({ value, isDisabled, onChange }: ModeSelectorProps): ReactElement {
  const descriptionId = useId();
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sidebar-foreground/70 text-xs font-medium">Modo de busca</span>
        <Popover>
          <PopoverTrigger asChild>
            <Button
              size="icon-sm"
              variant="ghost"
              className="text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground h-7 w-7"
              aria-label="Entender os modos de busca"
            >
              <CircleHelp aria-hidden="true" className="h-4 w-4" />
            </Button>
          </PopoverTrigger>
          <PopoverContent
            side="right"
            align="end"
            className="w-80 max-w-[calc(100vw-2rem)] space-y-3 text-sm"
            aria-label="Como funcionam os modos de busca"
          >
            <p className="font-semibold">Como buscar nas bulas</p>
            {Object.entries(RETRIEVAL_MODES).map(([mode, option]) => (
              <p key={mode}>
                <strong>{option.label}:</strong> {option.description}
              </p>
            ))}
          </PopoverContent>
        </Popover>
      </div>
      <Select
        value={value}
        disabled={isDisabled}
        onValueChange={(mode) => {
          if (isRetrievalMode(mode)) onChange(mode);
        }}
      >
        <SelectTrigger
          aria-label="Modo de busca"
          aria-describedby={descriptionId}
          className="border-sidebar-border bg-sidebar-accent text-sidebar-foreground hover:bg-sidebar-accent/80 [&_svg]:text-sidebar-foreground/60 w-full rounded-lg shadow-none"
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent className="border-sidebar-border bg-sidebar text-sidebar-foreground">
          {Object.entries(RETRIEVAL_MODES).map(([mode, option]) => (
            <SelectItem
              key={mode}
              value={mode}
              className="focus:bg-sidebar-accent focus:text-sidebar-foreground cursor-pointer py-2.5"
            >
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <p id={descriptionId} className="sr-only">
        {RETRIEVAL_MODES[value].description}
      </p>
    </div>
  );
}
