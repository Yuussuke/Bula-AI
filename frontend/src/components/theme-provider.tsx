"use client";
import { ThemeProvider as NextThemesProvider, type ThemeProviderProps } from "next-themes";
import type { ReactElement } from "react";

export function ThemeProvider({ children, ...props }: ThemeProviderProps): ReactElement {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
