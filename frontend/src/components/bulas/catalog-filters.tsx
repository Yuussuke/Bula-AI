import type { ReactElement } from "react";

import type { BulaAudience } from "@/api/bulas";

export type AudienceFilter = "all" | BulaAudience;

interface CatalogFiltersProps {
  audience: AudienceFilter;
  onChange: (audience: AudienceFilter) => void;
}

export function CatalogFilters({ audience, onChange }: CatalogFiltersProps): ReactElement {
  return (
    <select
      aria-label="Filtrar por público da bula"
      value={audience}
      onChange={(event) => {
        const value = event.currentTarget.value;
        onChange(value === "patient" || value === "professional" ? value : "all");
      }}
      className="border-input bg-card/45 h-9 rounded-md border px-3 text-sm backdrop-blur-md"
    >
      <option value="all">Todos os públicos</option>
      <option value="patient">Paciente</option>
      <option value="professional">Profissional de saúde</option>
    </select>
  );
}
