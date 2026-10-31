import type { ReactElement } from "react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

interface ActionHintProps {
  children: ReactElement;
  label: string;
  side?: "right" | "bottom";
}

export function ActionHint({ children, label, side = "right" }: ActionHintProps): ReactElement {
  return (
    <Tooltip delayDuration={180}>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent
        side={side}
        sideOffset={8}
        className="border-sidebar-border bg-sidebar-accent text-sidebar-foreground max-w-64 rounded-lg border px-3 py-2 text-xs shadow-lg duration-200 motion-reduce:animate-none [&>svg]:hidden"
      >
        {label}
      </TooltipContent>
    </Tooltip>
  );
}
