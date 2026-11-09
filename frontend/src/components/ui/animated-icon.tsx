import type { LucideIcon } from "lucide-react";
import {
  motion,
  stagger,
  useAnimate,
  useAnimationControls,
  useReducedMotion,
  type Variants,
} from "motion/react";
import { type ReactElement, useEffect } from "react";

import { cn } from "@/lib/utils";

// Shared interaction handling avoids duplicating a controller for every icon.
// Motion profiles follow the subtle interactions at https://lucide-animated.com/.
const animations = {
  nudge: { y: [0, -1.5, 0] },
  conversation: { rotate: [0, -7, 7, 0], scale: [1, 1.05, 1] },
  send: { x: [0, 3, 0], y: [0, -3, 0], scale: [1, 0.9, 1] },
  upload: { y: [0, -3, 0] },
  history: { rotate: [0, -35, 0] },
  panel: { x: [0, -2, 0] },
  logout: { x: [0, 3, 0] },
  theme: { rotate: [0, 25, 0] },
} satisfies Record<string, Variants[string]>;

interface AnimatedIconProps {
  icon: LucideIcon;
  effect?: keyof typeof animations;
  className?: string;
  animateOnMount?: boolean;
}

export function AnimatedIcon({
  icon: Icon,
  effect = "nudge",
  className,
  animateOnMount = false,
}: AnimatedIconProps): ReactElement {
  const [scope, animatePaths] = useAnimate<HTMLSpanElement>();
  const controls = useAnimationControls();
  const shouldReduceMotion = useReducedMotion();

  useEffect(() => {
    const action = scope.current?.closest("button, a, [role='button']");
    if (!action || shouldReduceMotion) return;
    let drawing: ReturnType<typeof animatePaths> | undefined;
    let isMoving = false;

    const animate = (): void => {
      if (isMoving || action.matches(":disabled, [aria-disabled='true']")) return;
      isMoving = true;
      void controls.start("active").then(() => {
        isMoving = false;
      });
    };
    const draw = (event?: Event): void => {
      if (event instanceof PointerEvent && event.pointerType === "touch") return;
      if (action.matches(":disabled, [aria-disabled='true']")) return;
      animate();
      drawing?.complete();
      drawing = animatePaths(
        "svg path, svg line, svg circle, svg ellipse, svg rect, svg polyline, svg polygon",
        { pathLength: [0, 1], opacity: [0.4, 1] },
        { duration: 0.55, delay: stagger(0.035), ease: "easeInOut" }
      );
    };
    const focus = (): void => {
      if (action.matches(":focus-visible")) draw();
    };
    const activate = (): void => {
      // A click keeps every stroke visible, even during an unfinished hover.
      drawing?.complete();
      animate();
    };
    const reset = (): void => {
      controls.stop();
      controls.set("rest");
      isMoving = false;
      drawing?.complete();
    };

    action.addEventListener("pointerenter", draw);
    action.addEventListener("focusin", focus);
    action.addEventListener("click", activate);
    action.addEventListener("pointerleave", reset);
    action.addEventListener("focusout", reset);
    if (animateOnMount) animate();
    return () => {
      action.removeEventListener("pointerenter", draw);
      action.removeEventListener("focusin", focus);
      action.removeEventListener("click", activate);
      action.removeEventListener("pointerleave", reset);
      action.removeEventListener("focusout", reset);
      controls.stop();
      drawing?.complete();
    };
  }, [animateOnMount, animatePaths, controls, scope, shouldReduceMotion]);

  return (
    <motion.span
      ref={scope}
      aria-hidden="true"
      className={cn("inline-flex size-4 shrink-0 items-center justify-center", className)}
      initial="rest"
      animate={shouldReduceMotion ? "rest" : controls}
      variants={{
        rest: { x: 0, y: 0, rotate: 0, scale: 1 },
        active: animations[effect],
      }}
      transition={{ duration: 0.45, ease: "easeInOut" }}
    >
      <Icon aria-hidden="true" className="size-full" />
    </motion.span>
  );
}
