import type { ReactElement } from "react";

import { cn } from "@/lib/utils";

export function AssistantAvatar({ className }: { className?: string }): ReactElement {
  return (
    <img
      src="/bula-ai-assistant.png"
      alt=""
      aria-hidden="true"
      width={1280}
      height={1280}
      className={cn("h-10 w-10 shrink-0 object-contain dark:brightness-150", className)}
    />
  );
}
