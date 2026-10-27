import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { useEffect } from "react";

import {
  type BulaStatus,
  type BulaStatusResponse,
  getBulaStatus,
  type UserBulaResponse,
} from "@/api/bulas";
import { userBulasQueryKey } from "@/hooks/use-user-bulas";

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
  const queryClient = useQueryClient();

  const result = useQuery({
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
  // Keep the personal list's filters/counts consistent with existing card polling.
  useEffect(() => {
    const status = result.data;
    if (!status) return;
    queryClient.setQueryData<UserBulaResponse[]>(userBulasQueryKey, (current) => {
      if (
        !current?.some(
          (item) =>
            item.id === status.id &&
            (item.status !== status.status ||
              item.drug_name !== status.drug_name ||
              item.alias !== status.alias ||
              item.manufacturer !== status.manufacturer ||
              item.error_message !== status.error_message)
        )
      )
        return current;
      return current.map((item) => (item.id === status.id ? { ...item, ...status } : item));
    });
  }, [queryClient, result.data]);
  return result;
}
