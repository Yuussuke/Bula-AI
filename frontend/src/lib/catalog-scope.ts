export const CATALOG_SCOPES = {
  all: "Catálogo Geral",
  system: "Catálogo ANVISA",
  shared: "Catálogo Compartilhado",
} as const;

export type CatalogScope = keyof typeof CATALOG_SCOPES;

export function isCatalogScope(value: unknown): value is CatalogScope {
  return value === "all" || value === "system" || value === "shared";
}

export function readCatalogScope(value: string | null): CatalogScope {
  return isCatalogScope(value) ? value : "all";
}

export function catalogParameters(scope: CatalogScope): URLSearchParams {
  return new URLSearchParams(scope === "all" ? {} : { catalogo: scope });
}

export function readCatalogReturnTo(state: unknown): string | null {
  if (typeof state !== "object" || state === null || !("returnTo" in state)) return null;
  const destination = state.returnTo;
  return typeof destination === "string" && /^\/catalogo(?:\?|$)/.test(destination)
    ? destination
    : null;
}
