import type { ReactElement } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CATALOG_SCOPES, type CatalogScope, isCatalogScope } from "@/lib/catalog-scope";

interface CatalogSelectorProps {
  value: CatalogScope;
  onChange: (scope: CatalogScope) => void;
  isDisabled?: boolean;
  isSidebar?: boolean;
}

export function CatalogSelector({
  value,
  onChange,
  isDisabled = false,
  isSidebar = false,
}: CatalogSelectorProps): ReactElement {
  return (
    <Select
      value={value}
      disabled={isDisabled}
      onValueChange={(scope) => {
        if (isCatalogScope(scope)) onChange(scope);
      }}
    >
      <SelectTrigger
        aria-label="Catálogo consultado"
        className={
          isSidebar
            ? "border-sidebar-border bg-sidebar-accent text-sidebar-foreground w-full rounded-lg shadow-none"
            : "w-full rounded-lg sm:w-auto sm:min-w-56"
        }
      >
        <SelectValue />
      </SelectTrigger>
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
