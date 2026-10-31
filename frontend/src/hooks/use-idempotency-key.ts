import { useCallback, useRef } from "react";

export function useIdempotencyKey(): {
  keyFor: (payload: string) => string;
  reset: () => void;
} {
  const current = useRef<{ payload: string; key: string } | null>(null);
  const keyFor = useCallback((payload: string): string => {
    if (current.current?.payload !== payload) {
      current.current = { payload, key: crypto.randomUUID() };
    }
    return current.current.key;
  }, []);
  const reset = useCallback((): void => {
    current.current = null;
  }, []);
  return { keyFor, reset };
}
