import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { listSystemBulas, type SystemBulaResponse } from "@/api/bulas";

const SYSTEM_BULA_LIST_LIMIT = 100;

export const systemBulasQueryKey = [
  "system-bulas",
  { limit: SYSTEM_BULA_LIST_LIMIT, offset: 0 },
] as const;

export function useSystemBulas(): UseQueryResult<SystemBulaResponse[], Error> {
  return useQuery({
    queryKey: systemBulasQueryKey,
    queryFn: () => listSystemBulas({ limit: SYSTEM_BULA_LIST_LIMIT, offset: 0 }),
  });
}
