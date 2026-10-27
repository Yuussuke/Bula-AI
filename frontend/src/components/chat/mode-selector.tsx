import type { ReactElement } from "react";

import type { RetrievalMode } from "@/api/chat";
import { isRetrievalMode, RETRIEVAL_MODES } from "@/lib/retrieval-mode";

interface ModeSelectorProps {
  value: RetrievalMode;
  isDisabled: boolean;
  onChange: (mode: RetrievalMode) => void;
}

export function ModeSelector({ value, isDisabled, onChange }: ModeSelectorProps): ReactElement {
  return (
    <div className="border-border space-y-1 border-b px-4 py-3">
      <label htmlFor="retrieval-mode" className="mr-2 text-sm font-medium">
        Modo de busca
      </label>
      <select
        id="retrieval-mode"
        value={value}
        disabled={isDisabled}
        aria-describedby="retrieval-mode-help"
        className="bg-background rounded-md border px-2 py-1 text-sm"
        onChange={(event) => {
          if (isRetrievalMode(event.target.value)) onChange(event.target.value);
        }}
      >
        {Object.entries(RETRIEVAL_MODES).map(([mode, option]) => (
          <option key={mode} value={mode}>
            {option.label}
          </option>
        ))}
      </select>
      <p id="retrieval-mode-help" className="text-muted-foreground text-xs">
        {RETRIEVAL_MODES[value].description}
      </p>
    </div>
  );
}
