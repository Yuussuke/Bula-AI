import { Moon, Sun } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useTheme } from "next-themes";
import type { ReactElement } from "react";

import { ActionHint } from "@/components/ui/action-hint";
import { AnimatedIcon } from "@/components/ui/animated-icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function ThemeToggle({ className }: { className?: string }): ReactElement {
  const { resolvedTheme, setTheme } = useTheme();
  const shouldReduceMotion = useReducedMotion();
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
        <AnimatePresence initial={false} mode="wait">
          <motion.span
            key={isDark ? "moon" : "sun"}
            aria-hidden="true"
            className="inline-flex"
            initial={{ opacity: 0, rotate: -90, scale: 0.5 }}
            animate={{ opacity: 1, rotate: 0, scale: 1 }}
            exit={{ opacity: 0, rotate: 90, scale: 0.5 }}
            transition={{ duration: shouldReduceMotion ? 0 : 0.18 }}
          >
            <AnimatedIcon icon={isDark ? Moon : Sun} effect="theme" animateOnMount />
          </motion.span>
        </AnimatePresence>
      </Button>
    </ActionHint>
  );
}
