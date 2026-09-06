import { Search } from "lucide-react";
import type { ReactElement } from "react";

import { Badge } from "@/components/ui/badge";

export function ModeIndicator(): ReactElement {
  return (
    <Badge variant="outline" className="gap-1.5 whitespace-nowrap">
      <Search aria-hidden="true" className="h-3.5 w-3.5" />
      Dense retrieval (beta)
    </Badge>
  );
}
