import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import {
  type BulaStatus,
  type BulaStatusResponse,
  getBulaStatus,
  type UserBulaResponse,
} from "@/api/bulas";

export const BULA_STATUS_POLL_INTERVAL_MS = 3_000;

export function isTerminalBulaStatus(status: BulaStatus): boolean {
  return status === "ready" || status === "error" || status === "failed";
}

export function useBulaStatus(
  bula: Pick<
    UserBulaResponse,
    "id" | "drug_name" | "alias" | "manufacturer" | "status" | "error_message"
  >
): UseQueryResult<BulaStatusResponse, Error> {
  const hasTerminalInitialStatus = isTerminalBulaStatus(bula.status);

  return useQuery({
    queryKey: ["user-bula-status", bula.id],
    queryFn: () => getBulaStatus(bula.id),
    initialData: {
      id: bula.id,
      drug_name: bula.drug_name,
      alias: bula.alias,
      manufacturer: bula.manufacturer,
      status: bula.status,
      error_message: bula.error_message,
    },
    enabled: !hasTerminalInitialStatus,
    refetchInterval: (statusQuery) => {
      const currentStatus = statusQuery.state.data?.status ?? bula.status;
      return isTerminalBulaStatus(currentStatus) ? false : BULA_STATUS_POLL_INTERVAL_MS;
    },
    refetchOnReconnect: false,
    refetchOnWindowFocus: false,
    retry: false,
  });
}
