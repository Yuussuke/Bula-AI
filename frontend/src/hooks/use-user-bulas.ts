import {
  useMutation,
  type UseMutationResult,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";

import {
  listUserBulas,
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
