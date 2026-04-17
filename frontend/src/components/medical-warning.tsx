"use client"

import { AlertCircle } from "lucide-react"

export function MedicalWarning() {
  return (
    <div className="bg-accent/10 border-b border-accent/20 px-4 sm:px-6 py-3 flex items-start gap-3">
      <AlertCircle className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
      <p className="text-sm text-foreground">
        <span className="font-semibold">Aviso:</span> O Bula AI é um assistente informacional e não substitui a avaliação de um médico. Sempre consulte seu médico antes de fazer mudanças em sua medicação.
      </p>
    </div>
  )
}
