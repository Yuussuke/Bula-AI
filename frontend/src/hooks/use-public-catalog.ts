import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import {
  type PublicCatalogPage,
  type PublicCatalogSearchOptions,
  searchPublicCatalog,
} from "@/api/bulas";

export function usePublicCatalog(
  options: PublicCatalogSearchOptions
): UseQueryResult<PublicCatalogPage, Error> {
  return useQuery({
    queryKey: ["public-catalog", options],
    queryFn: () => searchPublicCatalog(options),
    staleTime: 30_000,
  });
}
