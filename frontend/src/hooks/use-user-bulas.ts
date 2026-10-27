import {
  useMutation,
  type UseMutationResult,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";

import {
  type BulaStatusResponse,
  listUserBulas,
  updateBulaAlias,
  uploadBula,
  type UploadBulaRequest,
  type UserBulaResponse,
} from "@/api/bulas";

export const userBulasQueryKey = ["user-bulas"] as const;

export function useUserBulas(): UseQueryResult<UserBulaResponse[], Error> {
  return useQuery({
    queryKey: userBulasQueryKey,
    queryFn: listUserBulas,
  });
}

export function useUploadBula(): UseMutationResult<UserBulaResponse, Error, UploadBulaRequest> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: uploadBula,
    onSuccess: (uploadedBula) => {
      queryClient.setQueryData<UserBulaResponse[]>(userBulasQueryKey, (currentBulas = []) => {
        const otherBulas = currentBulas.filter((bula) => bula.id !== uploadedBula.id);
        return [uploadedBula, ...otherBulas];
      });
    },
  });
}

export function useUpdateBulaAlias(
  bulaId: string
): UseMutationResult<UserBulaResponse, Error, string> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (alias: string) => updateBulaAlias(bulaId, alias.trim() || null),
    onSuccess: async (updatedBula) => {
      await queryClient.cancelQueries({ queryKey: ["user-bula-status", bulaId] });
      queryClient.setQueryData<UserBulaResponse[]>(userBulasQueryKey, (current) =>
        current?.map((item) => (item.id === bulaId ? updatedBula : item))
      );
      queryClient.setQueryData<BulaStatusResponse>(["user-bula-status", bulaId], (current) =>
        current ? { ...current, alias: updatedBula.alias } : current
      );
      void queryClient.invalidateQueries({ queryKey: ["queryable-bula", bulaId] });
    },
  });
}
