import { useQuery } from "@tanstack/react-query";
import { History } from "lucide-react";
import type { ReactElement } from "react";
import { useNavigate } from "react-router-dom";

import { listChatSessions } from "@/api/chat";
import { Button } from "@/components/ui/button";

export function ResumeBulaChat({ bulaId }: { bulaId: string }): ReactElement {
  const navigate = useNavigate();
  const recentSession = useQuery({
    queryKey: ["recent-bula-chat", bulaId],
    queryFn: () => listChatSessions({ scope: "bula", bulaId, sort: "updated_at", limit: 1 }),
    enabled: false,
    retry: false,
  });
  const handleResume = async (): Promise<void> => {
    const result = await recentSession.refetch();
    const session = result.data?.[0];
    if (!result.isError && session?.bula_id === bulaId && (session.scope ?? "bula") === "bula") {
      void navigate(`/bulas/${bulaId}/chat?session=${session.id}`);
    }
  };
  return (
    <div className="w-full">
      <Button
        variant="ghost"
        size="sm"
        className="w-full"
        onClick={() => void handleResume()}
        disabled={recentSession.isFetching}
      >
        <History aria-hidden="true" className="mr-2 h-4 w-4" />
        {recentSession.isFetching ? "Buscando conversa…" : "Retomar última conversa"}
      </Button>
      {recentSession.isError ? (
        <p role="alert" className="text-destructive mt-1 text-xs">
          Não foi possível buscar a conversa. Tente novamente.
        </p>
      ) : null}
      {recentSession.isSuccess && recentSession.data.length === 0 ? (
        <p role="status" className="text-muted-foreground mt-1 text-xs">
          Nenhuma conversa anterior. Inicie uma nova acima.
        </p>
      ) : null}
    </div>
  );
}
