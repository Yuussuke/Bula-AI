import { Search } from "lucide-react";
import type { ChangeEvent, ReactElement } from "react";

import type { BulaAudience } from "@/api/bulas";
import { Input } from "@/components/ui/input";

export type AudienceFilter = "all" | BulaAudience;

interface SystemBulaFiltersProps {
  searchTerm: string;
  audience: AudienceFilter;
  onSearchTermChange: (searchTerm: string) => void;
  onAudienceChange: (audience: AudienceFilter) => void;
}

export function SystemBulaFilters({
  searchTerm,
  audience,
  onSearchTermChange,
  onAudienceChange,
}: SystemBulaFiltersProps): ReactElement {
  const handleAudienceChange = (event: ChangeEvent<HTMLSelectElement>): void => {
    onAudienceChange(event.target.value as AudienceFilter);
  };

  return (
    <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_13rem]">
      <div className="relative">
        <Search
          aria-hidden="true"
          className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2"
        />
        <Input
          type="search"
          value={searchTerm}
          onChange={(event) => onSearchTermChange(event.target.value)}
          placeholder="Buscar medicamento, princípio ativo ou fabricante"
          aria-label="Buscar no catálogo de bulas"
          className="pl-9"
        />
      </div>

      <label className="sr-only" htmlFor="bula-audience-filter">
        Filtrar por público da bula
      </label>
      <select
        id="bula-audience-filter"
        value={audience}
        onChange={handleAudienceChange}
        className="border-input bg-background focus-visible:border-ring focus-visible:ring-ring/50 h-9 rounded-md border px-3 text-sm shadow-xs outline-none focus-visible:ring-[3px]"
      >
        <option value="all">Todos os públicos</option>
        <option value="patient">Paciente</option>
        <option value="professional">Profissional de saúde</option>
      </select>
    </div>
  );
}
