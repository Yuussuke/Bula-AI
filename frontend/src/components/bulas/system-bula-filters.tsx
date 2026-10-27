import { Search } from "lucide-react";
import { type FormEvent, type ReactElement, useEffect, useRef } from "react";

import type { BulaAudience } from "@/api/bulas";
import { Input } from "@/components/ui/input";

export type AudienceFilter = "all" | BulaAudience;
export type CatalogSort = "name_asc" | "name_desc";

const SEARCH_DELAY_MS = 350;

interface SystemBulaFiltersProps {
  searchTerm: string;
  audience: AudienceFilter;
  sort: CatalogSort;
  onSearch: (searchTerm: string, audience: AudienceFilter, sort: CatalogSort) => void;
}

export function SystemBulaFilters({
  searchTerm,
  audience,
  sort,
  onSearch,
}: SystemBulaFiltersProps): ReactElement {
  const inputRef = useRef<HTMLInputElement>(null);
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancelPendingSearch = (): void => {
    if (searchTimerRef.current !== null) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = null;
  };

  // Keep browser back/forward and reset actions in sync without remounting the input.
  useEffect(() => {
    if (inputRef.current) inputRef.current.value = searchTerm;
    return () => {
      if (searchTimerRef.current !== null) clearTimeout(searchTimerRef.current);
    };
  }, [searchTerm, audience, sort]);

  const applyFilters = (nextAudience = audience, nextSort = sort): void => {
    cancelPendingSearch();
    const query = inputRef.current?.value.trim() ?? searchTerm;
    if (query !== searchTerm || nextAudience !== audience || nextSort !== sort) {
      onSearch(query, nextAudience, nextSort);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    applyFilters();
  };
  return (
    <form
      onSubmit={handleSubmit}
      className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_12rem_10rem]"
      role="search"
      aria-label="Buscar no Catálogo ANVISA"
    >
      <div className="relative sm:col-span-2 lg:col-span-1">
        <Search
          aria-hidden="true"
          className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2"
        />
        <Input
          ref={inputRef}
          name="query"
          type="search"
          defaultValue={searchTerm}
          onChange={(event) => {
            cancelPendingSearch();
            const query = event.currentTarget.value.trim();
            searchTimerRef.current = setTimeout(() => {
              if (query !== searchTerm) onSearch(query, audience, sort);
            }, SEARCH_DELAY_MS);
          }}
          maxLength={200}
          placeholder="Nome, princípio ativo, fabricante ou concentração"
          aria-label="Buscar no catálogo de bulas"
          className="pl-9"
        />
      </div>
      <label className="sr-only" htmlFor="bula-audience-filter">
        Filtrar por público da bula
      </label>
      <select
        name="audience"
        id="bula-audience-filter"
        value={audience}
        onChange={(event) => {
          const value = event.currentTarget.value;
          applyFilters(value === "patient" || value === "professional" ? value : "all");
        }}
        className="border-input bg-background h-9 rounded-md border px-3 text-sm"
      >
        <option value="all">Todos os públicos</option>
        <option value="patient">Paciente</option>
        <option value="professional">Profissional de saúde</option>
      </select>
      <label className="sr-only" htmlFor="catalog-sort">
        Ordenar catálogo
      </label>
      <select
        id="catalog-sort"
        value={sort}
        className="border-input bg-background h-9 rounded-md border px-3 text-sm"
        onChange={(event) =>
          applyFilters(
            audience,
            event.currentTarget.value === "name_desc" ? "name_desc" : "name_asc"
          )
        }
      >
        <option value="name_asc">Nome: A–Z</option>
        <option value="name_desc">Nome: Z–A</option>
      </select>
    </form>
  );
}
