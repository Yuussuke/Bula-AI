import { Search } from "lucide-react";
import type { ReactElement } from "react";

import type { RetrievalMode } from "@/api/chat";
import { Badge } from "@/components/ui/badge";
import { isRetrievalMode, RETRIEVAL_MODES } from "@/lib/retrieval-mode";

export function ModeIndicator({ mode = "hybrid" }: { mode?: RetrievalMode | null }): ReactElement {
  return (
    <Badge variant="outline" className="gap-1.5 whitespace-nowrap">
      <Search aria-hidden="true" className="h-3.5 w-3.5" />
      {isRetrievalMode(mode) ? RETRIEVAL_MODES[mode].label : "Modo não informado"}
    </Badge>
  );
}
