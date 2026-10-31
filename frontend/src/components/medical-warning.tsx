"use client";

import { Info } from "lucide-react";
import type { ReactElement } from "react";

export function MedicalWarning(): ReactElement {
  return (
    <div
      role="note"
      aria-label="Aviso sobre o Bula AI"
      className="mb-3 flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm leading-relaxed text-amber-950 dark:border-amber-800/60 dark:bg-amber-950/35 dark:text-amber-100"
    >
      <Info
        aria-hidden="true"
        className="mt-0.5 h-4 w-4 shrink-0 text-amber-700 dark:text-amber-300"
      />
      <p>
        <strong className="font-semibold">Importante:</strong> O Bula AI consulta bulas e não
        substitui a orientação de um profissional de saúde.
      </p>
    </div>
  );
}
