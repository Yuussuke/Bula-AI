import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import type { ReactElement } from "react";

import { ActionHint } from "@/components/ui/action-hint";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function ThemeToggle({ className }: { className?: string }): ReactElement {
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  const label = isDark ? "Ativar tema claro" : "Ativar tema escuro";
  return (
    <ActionHint label={label}>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className={cn("relative shrink-0 overflow-hidden", className)}
        aria-label={label}
        aria-pressed={isDark}
        onClick={() => setTheme(isDark ? "light" : "dark")}
      >
        <Sun
          aria-hidden="true"
          className="h-4 w-4 scale-100 rotate-0 opacity-100 transition-[transform,opacity] duration-300 motion-reduce:transition-none dark:scale-0 dark:-rotate-90 dark:opacity-0"
        />
        <Moon
          aria-hidden="true"
          className="absolute h-4 w-4 scale-0 rotate-90 opacity-0 transition-[transform,opacity] duration-300 motion-reduce:transition-none dark:scale-100 dark:rotate-0 dark:opacity-100"
        />
      </Button>
    </ActionHint>
  );
}
