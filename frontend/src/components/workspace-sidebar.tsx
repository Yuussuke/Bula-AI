import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { type ReactElement, type ReactNode, useId, useRef, useState } from "react";
import { NavLink } from "react-router-dom";

import { BrandLogo } from "@/components/brand-logo";
import { ActionHint } from "@/components/ui/action-hint";
import { Button } from "@/components/ui/button";
import { UserInitialsAvatar } from "@/components/user-initials-avatar";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";
import { useSidebarStore } from "@/store/sidebar";

const RAIL_WIDTH = 56;
const EXPANDED_WIDTH = 288;

export const sidebarShortcutClass =
  "text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-foreground flex h-11 min-h-11 w-11 shrink-0 items-center justify-center rounded-xl";

interface WorkspaceSidebarProps {
  children: ReactNode;
  shortcuts: ReactNode;
  collapsedControls?: ReactNode;
  navigationLabel?: string;
}

export function WorkspaceSidebar({
  children,
  shortcuts,
  collapsedControls,
  navigationLabel = "Atalhos do chat",
}: WorkspaceSidebarProps): ReactElement {
  const isCollapsed = useSidebarStore((state) => state.isCollapsed);
  const user = useAuthStore((state) => state.user);
  const setCollapsed = useSidebarStore((state) => state.setCollapsed);
  const [dragWidth, setDragWidth] = useState<number | null>(null);
  const gestureRef = useRef<{ startX: number; startWidth: number } | null>(null);
  const hasDraggedRef = useRef(false);
  const panelId = useId();
  const toggleLabel = isCollapsed ? "Expandir barra lateral" : "Recolher barra lateral";
  const isPanelHidden = isCollapsed && dragWidth === null;
  const clampWidth = (width: number): number =>
    Math.max(RAIL_WIDTH, Math.min(EXPANDED_WIDTH, width));
  const getDragWidth = (startWidth: number, delta: number): number => {
    const widthRange = EXPANDED_WIDTH - RAIL_WIDTH;
    const progress = Math.min(Math.abs(delta) / widthRange, 1);
    // Continuous acceleration: a small pull moves gently, then gains speed.
    const distance = widthRange * progress ** 1.6;
    return clampWidth(startWidth + Math.sign(delta) * distance);
  };

  return (
    <aside
      className={cn(
        "bg-sidebar text-sidebar-foreground border-sidebar-border relative h-full shrink-0 border-r motion-reduce:transition-none",
        dragWidth === null && "transition-[width] duration-250 ease-in-out"
      )}
      style={{ width: dragWidth ?? (isCollapsed ? RAIL_WIDTH : EXPANDED_WIDTH) }}
    >
      <div className="flex h-full overflow-hidden">
        <div className="border-sidebar-border z-10 flex w-14 shrink-0 flex-col border-r">
          <nav
            aria-label={navigationLabel}
            className="sidebar-scroll flex min-h-0 flex-1 flex-col items-center gap-2 overflow-y-auto overscroll-contain py-3"
          >
            <ActionHint label="Bula AI — início">
              <Button asChild variant="ghost" size="icon" className={sidebarShortcutClass}>
                <NavLink to="/" end aria-label="Início">
                  <BrandLogo variant="white" className="h-7 w-9" />
                </NavLink>
              </Button>
            </ActionHint>
            <ActionHint label={toggleLabel}>
              <Button
                variant="ghost"
                size="icon"
                className={sidebarShortcutClass}
                aria-label={toggleLabel}
                aria-expanded={!isCollapsed}
                aria-controls={panelId}
                onClick={() => setCollapsed(!isCollapsed)}
              >
                {isCollapsed ? (
                  <PanelLeftOpen aria-hidden="true" />
                ) : (
                  <PanelLeftClose aria-hidden="true" />
                )}
              </Button>
            </ActionHint>
            {shortcuts}
            {isCollapsed && collapsedControls ? (
              <div className="mt-auto flex flex-col items-center gap-1 pt-3">
                {collapsedControls}
              </div>
            ) : null}
          </nav>
          <div className="flex shrink-0 flex-col items-center gap-2 py-3">
            <ActionHint label={user?.name ?? "Usuário"}>
              <span>
                <UserInitialsAvatar name={user?.name} />
              </span>
            </ActionHint>
          </div>
        </div>
        <div
          id={panelId}
          aria-hidden={isPanelHidden}
          inert={isPanelHidden}
          className={cn(
            "flex h-full w-58 shrink-0 flex-col transition-opacity duration-200 motion-reduce:transition-none",
            isPanelHidden ? "pointer-events-none opacity-0" : "opacity-100"
          )}
        >
          {children}
        </div>
      </div>
      <button
        type="button"
        aria-label="Ajustar barra lateral"
        aria-expanded={!isCollapsed}
        aria-controls={panelId}
        title="Arraste para ajustar; dê dois cliques ou use as setas para recolher ou expandir"
        className="hover:bg-primary/15 focus-visible:bg-primary/20 absolute inset-y-0 -right-1 z-20 w-2 cursor-col-resize touch-none rounded-sm transition-colors focus-visible:outline-2"
        onPointerDown={(event) => {
          if (event.button !== 0) return;
          hasDraggedRef.current = false;
          gestureRef.current = {
            startX: event.clientX,
            startWidth: isCollapsed ? RAIL_WIDTH : EXPANDED_WIDTH,
          };
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          const gesture = gestureRef.current;
          if (gesture === null) return;
          const delta = event.clientX - gesture.startX;
          if (Math.abs(delta) < 3 && !hasDraggedRef.current) return;
          hasDraggedRef.current = true;
          setDragWidth(getDragWidth(gesture.startWidth, delta));
        }}
        onPointerUp={(event) => {
          const gesture = gestureRef.current;
          gestureRef.current = null;
          if (gesture !== null && hasDraggedRef.current) {
            const width = getDragWidth(gesture.startWidth, event.clientX - gesture.startX);
            setCollapsed(width < (EXPANDED_WIDTH + RAIL_WIDTH) / 2);
          }
          setDragWidth(null);
          if (event.currentTarget.hasPointerCapture(event.pointerId))
            event.currentTarget.releasePointerCapture(event.pointerId);
        }}
        onPointerCancel={() => {
          gestureRef.current = null;
          hasDraggedRef.current = false;
          setDragWidth(null);
        }}
        onClick={(event) => {
          // Pointer clicks belong to the double-click gesture; keyboard activation stays available.
          if (event.detail === 0) setCollapsed(!isCollapsed);
        }}
        onDoubleClick={() => {
          if (!hasDraggedRef.current) setCollapsed(!isCollapsed);
        }}
        onKeyDown={(event) => {
          if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
          event.preventDefault();
          setCollapsed(event.key === "ArrowLeft");
        }}
      />
    </aside>
  );
}
