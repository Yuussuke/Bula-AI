import { Library } from "lucide-react";
import type { ReactElement } from "react";

import { ActionHint } from "@/components/ui/action-hint";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CATALOG_SCOPES, type CatalogScope, isCatalogScope } from "@/lib/catalog-scope";
import { cn } from "@/lib/utils";

interface CatalogSelectorProps {
  value: CatalogScope;
  onChange: (scope: CatalogScope) => void;
  isDisabled?: boolean;
  isSidebar?: boolean;
  variant?: "default" | "compact" | "icon";
}

const compactLabels: Record<CatalogScope, string> = {
  all: "Geral",
  system: "ANVISA",
  shared: "Compartilhado",
};

export function CatalogSelector({
  value,
  onChange,
  isDisabled = false,
  isSidebar = false,
  variant = "default",
}: CatalogSelectorProps): ReactElement {
  const trigger = (
    <SelectTrigger
      aria-label="Catálogo consultado"
      className={cn(
        "rounded-lg shadow-none",
        isSidebar
          ? "border-sidebar-border text-sidebar-foreground hover:bg-sidebar-accent"
          : "hover:bg-muted",
        variant === "default"
          ? "w-full sm:w-auto sm:min-w-56"
          : "gap-2 border-transparent bg-transparent",
        variant === "compact" && "w-auto shrink-0 gap-1.5 px-2",
        variant === "icon" &&
          "w-11 justify-center px-0 data-[size=default]:h-11 [&>svg:last-child]:hidden"
      )}
    >
      {variant !== "default" ? <Library aria-hidden="true" className="h-4 w-4" /> : null}
      <SelectValue>
        <span
          className={
            variant === "icon"
              ? "sr-only"
              : variant === "compact"
                ? "sr-only sm:not-sr-only"
                : undefined
          }
        >
          {variant === "default" ? CATALOG_SCOPES[value] : compactLabels[value]}
        </span>
      </SelectValue>
    </SelectTrigger>
  );
  return (
    <Select
      value={value}
      disabled={isDisabled}
      onValueChange={(scope) => {
        if (isCatalogScope(scope)) onChange(scope);
      }}
    >
      {variant === "default" ? (
        trigger
      ) : (
        <ActionHint
          side={variant === "icon" ? "right" : "bottom"}
          label={`${CATALOG_SCOPES[value]}. Trocar o catálogo inicia outra conversa.`}
        >
          {trigger}
        </ActionHint>
      )}
      <SelectContent
        className={
          isSidebar ? "border-sidebar-border bg-sidebar text-sidebar-foreground" : undefined
        }
      >
        {Object.entries(CATALOG_SCOPES).map(([scope, label]) => (
          <SelectItem
            key={scope}
            value={scope}
            className={
              isSidebar ? "focus:bg-sidebar-accent focus:text-sidebar-foreground" : undefined
            }
          >
            {label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
