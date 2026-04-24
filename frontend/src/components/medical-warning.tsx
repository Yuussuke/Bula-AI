"use client";

import { AlertCircle } from "lucide-react";

export function MedicalWarning() {
  return (
    <div className="bg-accent/10 border-accent/20 flex items-start gap-3 border-b px-4 py-3 sm:px-6">
      <AlertCircle className="text-accent mt-0.5 h-5 w-5 flex-shrink-0" />
      <p className="text-foreground text-sm">
        <span className="font-semibold">Aviso:</span> O Bula AI é um assistente informacional e não
        substitui a avaliação de um médico. Sempre consulte seu médico antes de fazer mudanças em
        sua medicação.
      </p>
    </div>
  );
}
