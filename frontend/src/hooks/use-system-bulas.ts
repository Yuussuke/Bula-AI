import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { searchSystemBulas, type SystemBulaPage, type SystemBulaSearchOptions } from "@/api/bulas";

export function useSystemBulas(
  options: SystemBulaSearchOptions
): UseQueryResult<SystemBulaPage, Error> {
  return useQuery({
    queryKey: ["system-bulas", options],
    queryFn: () => searchSystemBulas(options),
    staleTime: 30_000,
  });
}
