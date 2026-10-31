import { User } from "lucide-react";
import type { ReactElement } from "react";

interface UserInitialsAvatarProps {
  name?: string;
}

export function UserInitialsAvatar({ name }: UserInitialsAvatarProps): ReactElement {
  const nameParts = name?.trim().split(/\s+/).filter(Boolean) ?? [];
  const initials = [nameParts[0], nameParts.length > 1 ? nameParts.at(-1) : undefined]
    .filter((part): part is string => part !== undefined)
    .map((part) => Array.from(part)[0])
    .join("")
    .toLocaleUpperCase("pt-BR");

  return (
    <span
      role="img"
      aria-label={name?.trim() || "Usuário"}
      className="bg-sidebar-accent text-sidebar-accent-foreground flex h-9 w-9 items-center justify-center rounded-full text-xs font-semibold"
    >
      {initials || <User aria-hidden="true" className="h-4 w-4" />}
    </span>
  );
}
