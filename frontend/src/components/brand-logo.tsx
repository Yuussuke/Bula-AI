import type { ReactElement } from "react";

import { BRAND_BODY_PATH, BRAND_DOTS } from "@/components/brand-logo-geometry";
import { cn } from "@/lib/utils";

interface BrandLogoProps {
  className?: string;
  variant?: "brand" | "white";
}

export function BrandLogo({ className, variant = "brand" }: BrandLogoProps): ReactElement {
  return (
    <svg
      viewBox="0 0 1257 960"
      fill="currentColor"
      aria-hidden="true"
      width={1257}
      height={960}
      className={cn(
        "brand-mark h-8 w-10 shrink-0",
        variant === "white" ? "text-white" : "text-[#007c68]",
        className
      )}
    >
      <path fillRule="evenodd" d={BRAND_BODY_PATH} />
      <g>
        {BRAND_DOTS.map((dot, index) => (
          <circle key={dot.cx} className={`brand-dot brand-dot-${index + 1}`} {...dot} />
        ))}
      </g>
    </svg>
  );
}
