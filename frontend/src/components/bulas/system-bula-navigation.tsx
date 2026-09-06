import { FileText } from "lucide-react";
import { type ReactElement, useMemo } from "react";
import { Link } from "react-router-dom";

import { Skeleton } from "@/components/ui/skeleton";
import { useSystemBulas } from "@/hooks/use-system-bulas";

interface SystemBulaNavigationProps {
  onNavigate?: () => void;
}

export function SystemBulaNavigation({ onNavigate }: SystemBulaNavigationProps): ReactElement {
  const systemBulasQuery = useSystemBulas();
  const availableBulas = useMemo(
    () =>
      (systemBulasQuery.data ?? []).filter(
        (bula) => bula.publication_state === "published" && bula.ingestion_status === "ready"
      ),
    [systemBulasQuery.data]
  );

  return (
    <section className="mt-6" aria-labelledby="available-bulas-title">
      <h2
        id="available-bulas-title"
        className="text-sidebar-foreground/55 mb-2 px-2 text-xs font-semibold tracking-wide uppercase"
      >
        Bulas disponíveis
      </h2>

      {systemBulasQuery.isLoading ? (
        <div role="status" aria-label="Carregando bulas disponíveis" className="space-y-2 px-1">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      ) : null}

      {systemBulasQuery.isError ? (
        <p className="text-sidebar-foreground/60 px-2 py-2 text-xs">
          Não foi possível carregar as bulas.
        </p>
      ) : null}

      {systemBulasQuery.isSuccess && availableBulas.length === 0 ? (
        <p className="text-sidebar-foreground/60 px-2 py-2 text-xs">
          Nenhuma bula pronta para conversa.
        </p>
      ) : null}

      {availableBulas.length > 0 ? (
        <ul className="space-y-1">
          {availableBulas.map((bula) => (
            <li key={bula.id}>
              <Link
                to={`/bulas/${bula.id}/chat`}
                aria-label={`Conversar sobre ${bula.product_name}, ${bula.strength}`}
                onClick={onNavigate}
                className="text-sidebar-foreground/75 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground flex items-start gap-2.5 rounded-lg px-3 py-2.5 transition-colors"
              >
                <FileText aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
                <span className="min-w-0">
                  <span className="line-clamp-2 block text-sm leading-snug font-medium">
                    {bula.product_name}
                  </span>
                  <span className="mt-0.5 block truncate text-xs opacity-65">{bula.strength}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
