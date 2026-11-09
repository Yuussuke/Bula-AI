import { useInfiniteQuery } from "@tanstack/react-query";
import { BookOpenText, MessageSquareText, Search, X } from "lucide-react";
import { type FormEvent, type ReactElement, useEffect, useId, useRef, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";

import { searchWorkspace, type WorkspaceSearchKind } from "@/api/chat";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { getChatSessionPath } from "@/lib/chat-navigation";
import { useAuthStore } from "@/store/auth";

const filters: { value: WorkspaceSearchKind; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "chats", label: "Chats" },
  { value: "medications", label: "Medicamentos" },
];
const dateFormatter = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" });
const resultClassName =
  "hover:bg-accent focus-visible:bg-accent focus-visible:ring-primary flex min-w-0 items-start gap-2 rounded-lg px-2 py-2 text-sm outline-none focus-visible:ring-1 focus-visible:ring-inset";

export function WorkspaceSearch(): ReactElement {
  const location = useLocation();
  const [parameters, setParameters] = useSearchParams();
  const isCatalogPage = location.pathname === "/catalogo";
  const catalogSearchTerm = parameters.get("q") ?? "";
  const userId = useAuthStore((state) => state.user?.id);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const [kind, setKind] = useState<WorkspaceSearchKind>("all");
  const catalogTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const resultsId = useId();
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  // Restore the catalog query on navigation, reset and browser back/forward.
  useEffect(() => {
    if (inputRef.current) inputRef.current.value = isCatalogPage ? catalogSearchTerm : query;
    return () => {
      if (catalogTimerRef.current !== null) clearTimeout(catalogTimerRef.current);
    };
  }, [isCatalogPage, catalogSearchTerm, location.search, query]);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const root = rootRef.current;
    if (!isOpen || !root) return;
    const closeOutside = (event: Event): void => {
      if (event.target instanceof Node && !rootRef.current?.contains(event.target))
        setIsOpen(false);
    };
    const navigateResults = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        event.preventDefault();
        inputRef.current?.focus();
        setIsOpen(false);
        return;
      }
      if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
      const links = Array.from(root.querySelectorAll<HTMLAnchorElement>("a[href]"));
      if (links.length === 0) return;
      event.preventDefault();
      const currentIndex = links.findIndex((link) => link === document.activeElement);
      const direction = event.key === "ArrowDown" ? 1 : -1;
      const nextIndex =
        currentIndex === -1 ? (direction === 1 ? 0 : links.length - 1) : currentIndex + direction;
      if (nextIndex < 0 || nextIndex >= links.length) inputRef.current?.focus();
      else links[nextIndex]?.focus();
    };
    root.addEventListener("keydown", navigateResults);
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("focusin", closeOutside);
    return () => {
      root.removeEventListener("keydown", navigateResults);
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("focusin", closeOutside);
    };
  }, [isOpen]);

  const hasQuery = query.trim().length >= 2;
  const isUpdatingQuery = query.trim() !== debouncedQuery;
  const canSearch = !isCatalogPage && isOpen && hasQuery && !isUpdatingQuery;
  const resultsQuery = useInfiniteQuery({
    queryKey: ["workspace-search", userId, debouncedQuery, kind],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam, signal }) =>
      searchWorkspace({ query: debouncedQuery, kind, cursor: pageParam }, signal),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    enabled: canSearch && userId !== undefined,
    staleTime: 30_000,
  });
  const results = resultsQuery.data?.pages.flatMap((page) => page.items) ?? [];
  const isSearching = isUpdatingQuery || resultsQuery.isLoading;
  const catalogPath = `/catalogo?${new URLSearchParams({ q: debouncedQuery }).toString()}`;

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = 0;
  }, [debouncedQuery, kind]);

  const updateCatalogSearch = (value: string): void => {
    const next = new URLSearchParams(parameters);
    const term = value.trim();
    if (term) next.set("q", term);
    else next.delete("q");
    next.delete("pagina");
    next.delete("ordem");
    setParameters(next, { replace: true });
  };

  const submitSearch = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (isCatalogPage) {
      if (catalogTimerRef.current !== null) clearTimeout(catalogTimerRef.current);
      updateCatalogSearch(inputRef.current?.value ?? "");
      return;
    }
    if (!hasQuery) return;
    setIsOpen(true);
    listRef.current?.querySelector<HTMLAnchorElement>("a[href]")?.focus();
  };

  return (
    <div ref={rootRef} className="pointer-events-auto relative mx-auto w-full max-w-lg min-w-0">
      <form
        role="search"
        aria-label="Pesquisar medicamentos e conversas"
        onSubmit={submitSearch}
        className="border-border/70 bg-card/45 focus-within:border-primary/50 flex h-10 items-center gap-2 rounded-xl border px-3 backdrop-blur-md"
      >
        <Search aria-hidden="true" className="text-muted-foreground h-4 w-4 shrink-0" />
        <Input
          ref={inputRef}
          type="search"
          aria-label="Pesquisar medicamentos e conversas"
          aria-controls={!isCatalogPage && isOpen && query.trim() ? resultsId : undefined}
          aria-describedby={`${resultsId}-help`}
          placeholder="Pesquisar medicamentos ou conversas..."
          defaultValue={isCatalogPage ? catalogSearchTerm : query}
          onFocus={() => setIsOpen(!isCatalogPage)}
          onClick={() => setIsOpen(!isCatalogPage)}
          onChange={(event) => {
            const value = event.currentTarget.value;
            if (isCatalogPage) {
              if (catalogTimerRef.current !== null) clearTimeout(catalogTimerRef.current);
              catalogTimerRef.current = setTimeout(() => updateCatalogSearch(value), 250);
            } else {
              setQuery(value);
              setIsOpen(true);
            }
          }}
          maxLength={200}
          autoComplete="off"
          className="h-9 border-0 bg-transparent px-0 text-base shadow-none focus-visible:ring-0 sm:text-sm dark:bg-transparent [&::-webkit-search-cancel-button]:appearance-none"
        />
        <button
          type="button"
          aria-label="Limpar pesquisa"
          className="text-muted-foreground hover:text-foreground shrink-0 rounded p-1 focus-visible:outline-2"
          onClick={() => {
            if (catalogTimerRef.current !== null) clearTimeout(catalogTimerRef.current);
            if (inputRef.current) inputRef.current.value = "";
            if (isCatalogPage) updateCatalogSearch("");
            else {
              setQuery("");
              setIsOpen(false);
            }
            inputRef.current?.focus();
          }}
        >
          <X aria-hidden="true" className="h-3.5 w-3.5" />
        </button>
      </form>
      <p id={`${resultsId}-help`} className="sr-only">
        {isCatalogPage
          ? "A lista do catálogo é atualizada enquanto você digita."
          : "Pesquise medicamentos, títulos ou suas mensagens. Use as setas para percorrer os resultados."}
      </p>
      {!isCatalogPage && isOpen && query.trim().length > 0 ? (
        <div
          id={resultsId}
          role="region"
          aria-label="Resultados da pesquisa"
          className="bg-popover/75 text-popover-foreground fixed inset-x-4 top-15 z-50 flex max-h-[min(50dvh,22rem)] flex-col overflow-hidden rounded-xl border p-2 shadow-lg backdrop-blur-xl sm:absolute sm:inset-x-0 sm:top-full sm:mt-2"
        >
          <div
            role="group"
            aria-label="Filtrar resultados"
            className="flex shrink-0 gap-1 border-b px-1 pb-2"
          >
            {filters.map((filter) => (
              <button
                key={filter.value}
                type="button"
                aria-pressed={kind === filter.value}
                onClick={() => setKind(filter.value)}
                className={`rounded-full px-3 py-1.5 text-xs transition-colors focus-visible:outline-2 ${kind === filter.value ? "bg-primary/15 text-primary" : "text-muted-foreground hover:bg-accent"}`}
              >
                {filter.label}
              </button>
            ))}
          </div>
          <div
            ref={listRef}
            className="clean-scroll min-h-0 overflow-y-auto overscroll-contain pt-1"
            onScroll={(event) => {
              const list = event.currentTarget;
              if (
                list.scrollHeight - list.scrollTop - list.clientHeight < 80 &&
                resultsQuery.hasNextPage &&
                !resultsQuery.isFetching &&
                !resultsQuery.isFetchNextPageError
              )
                void resultsQuery.fetchNextPage();
            }}
          >
            {!hasQuery ? (
              <p className="text-muted-foreground px-2 py-3 text-xs">
                Digite pelo menos dois caracteres.
              </p>
            ) : isSearching ? (
              <SearchLoading />
            ) : (
              <>
                <ul>
                  {results.map((result) => {
                    const isChat = result.kind === "chat";
                    const path = isChat
                      ? getChatSessionPath(result.session)
                      : `/bulas/${result.medication.id}/chat`;
                    const href =
                      path && isChat && result.message_id
                        ? `${path}&message=${result.message_id}`
                        : path;
                    const title = isChat ? result.session.title : result.medication.product_name;
                    const description = isChat
                      ? result.excerpt
                      : [
                          result.medication.strength,
                          result.medication.pharmaceutical_form,
                          result.medication.manufacturer,
                        ]
                          .filter(Boolean)
                          .join(" · ");
                    const key = isChat
                      ? `chat:${result.session.id}`
                      : `medication:${result.medication.id}`;
                    const Icon = isChat ? MessageSquareText : BookOpenText;
                    return (
                      <li key={key}>
                        {href ? (
                          <Link
                            to={href}
                            state={isChat ? undefined : { returnTo: catalogPath }}
                            onClick={() => setIsOpen(false)}
                            className={resultClassName}
                          >
                            <Icon aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
                            <span className="min-w-0 flex-1">
                              <span className="block truncate font-medium">{title}</span>
                              {description ? (
                                <span className="text-muted-foreground mt-1 line-clamp-2 text-xs [overflow-wrap:anywhere]">
                                  {description}
                                </span>
                              ) : null}
                            </span>
                            {isChat ? (
                              <time
                                dateTime={result.matched_at}
                                className="text-muted-foreground mt-0.5 shrink-0 text-[10px]"
                              >
                                {dateFormatter.format(new Date(result.matched_at))}
                              </time>
                            ) : null}
                          </Link>
                        ) : (
                          <p className="text-muted-foreground px-2 py-2 text-xs">
                            {title} — documento indisponível
                          </p>
                        )}
                      </li>
                    );
                  })}
                </ul>
                {resultsQuery.isSuccess && results.length === 0 ? (
                  <p className="text-muted-foreground px-2 py-3 text-xs">
                    Nenhum resultado encontrado.
                  </p>
                ) : null}
                {resultsQuery.isFetchingNextPage ? <SearchLoading /> : null}
                {resultsQuery.isError ? (
                  <p role="alert" className="text-muted-foreground px-2 py-2 text-xs">
                    Não foi possível{" "}
                    {results.length ? "carregar mais resultados" : "concluir a pesquisa"}.
                  </p>
                ) : null}
                {resultsQuery.hasNextPage || resultsQuery.isError ? (
                  <button
                    type="button"
                    disabled={resultsQuery.isFetching}
                    onClick={() => {
                      if (resultsQuery.isFetchNextPageError || resultsQuery.hasNextPage)
                        void resultsQuery.fetchNextPage();
                      else void resultsQuery.refetch();
                    }}
                    className="text-primary hover:bg-accent w-full rounded-lg px-2 py-2 text-xs focus-visible:outline-2"
                  >
                    {resultsQuery.isError ? "Tentar novamente" : "Carregar mais resultados"}
                  </button>
                ) : null}
              </>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function SearchLoading(): ReactElement {
  return (
    <div role="status" aria-label="Carregando resultados" className="space-y-3 px-2 py-3">
      {[0, 1, 2].map((index) => (
        <div key={index} className="flex gap-3">
          <Skeleton className="mt-1 h-4 w-4 shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3 w-2/5" />
            <Skeleton className="h-3 w-4/5" />
          </div>
        </div>
      ))}
    </div>
  );
}
