interface AuthLocationState {
  returnTo?: unknown;
}

export function getPostAuthPath(locationState: unknown): string {
  if (typeof locationState !== "object" || locationState === null) {
    return "/";
  }

  const returnTo = (locationState as AuthLocationState).returnTo;
  const isInternalPath =
    typeof returnTo === "string" && returnTo.startsWith("/") && !returnTo.startsWith("//");

  if (!isInternalPath || returnTo === "/auth") {
    return "/";
  }

  return returnTo;
}
