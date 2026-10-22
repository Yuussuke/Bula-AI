import { Search } from "lucide-react";
import type { ReactElement } from "react";

import type { RetrievalMode } from "@/api/chat";
import { Badge } from "@/components/ui/badge";

export function ModeIndicator({ mode = "hybrid" }: { mode?: RetrievalMode | null }): ReactElement {
  const labels = { dense: "Semântico", bm25: "Palavras-chave", hybrid: "Híbrido" };
  return (
    <Badge variant="outline" className="gap-1.5 whitespace-nowrap">
      <Search aria-hidden="true" className="h-3.5 w-3.5" />
      {mode ? labels[mode] : "Modo não informado"}
    </Badge>
  );
}
