import type { ReactElement } from "react";

import { cn } from "@/lib/utils";

interface BrandLogoProps {
  className?: string;
  variant?: "brand" | "white";
}

export function BrandLogo({ className, variant = "brand" }: BrandLogoProps): ReactElement {
  return (
    <img
      src="/bula-ai-logo.png"
      alt=""
      aria-hidden="true"
      width={1257}
      height={960}
      className={cn(
        "h-8 w-10 shrink-0 object-contain",
        variant === "white" && "brightness-0 invert",
        className
      )}
    />
  );
}
