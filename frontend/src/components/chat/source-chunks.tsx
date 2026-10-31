import { FileText } from "lucide-react";
import { lazy, type ReactElement, Suspense, useRef, useState } from "react";

import type { SourceChunkResponse } from "@/api/chat";
import { buildSourceChunkId } from "@/components/chat/source-chunk-navigation";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const MessageMarkdown = lazy(() => import("@/components/chat/message-markdown"));

function getSourceLink(value?: string | null): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}

interface SourceChunksProps {
  sourceChunks: SourceChunkResponse[];
  messageId?: string;
  isOpen?: boolean;
  onOpenChange?: (isOpen: boolean) => void;
  selectedCitation?: number;
}

export function SourceChunks({
  sourceChunks,
  messageId,
  isOpen: controlledIsOpen,
  onOpenChange,
  selectedCitation = 1,
}: SourceChunksProps): ReactElement | null {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const isOpen = controlledIsOpen ?? internalIsOpen;

  const handleOpenChange = (nextIsOpen: boolean): void => {
    setInternalIsOpen(nextIsOpen);
    onOpenChange?.(nextIsOpen);
  };

  if (sourceChunks.length === 0) {
    return null;
  }

  const sourceLabel =
    sourceChunks.length === 1 ? "1 referência" : `${sourceChunks.length} referências`;

  return (
    <Sheet open={isOpen} onOpenChange={handleOpenChange}>
      <SheetTrigger asChild>
        <Button type="button" variant="ghost" size="sm" className="h-8 gap-1.5 px-2 text-xs">
          <FileText aria-hidden="true" className="h-3.5 w-3.5" />
          Ver {sourceLabel}
        </Button>
      </SheetTrigger>
      <SheetContent
        className="w-full gap-0 sm:w-full sm:max-w-xl"
        onOpenAutoFocus={(event) => {
          returnFocusRef.current =
            document.activeElement instanceof HTMLElement ? document.activeElement : null;
          if (!messageId) return;
          const source = document.getElementById(buildSourceChunkId(messageId, selectedCitation));
          if (!source) return;
          event.preventDefault();
          source.focus({ preventScroll: true });
          source.scrollIntoView?.({ behavior: "auto", block: "start" });
        }}
        onCloseAutoFocus={(event) => {
          if (returnFocusRef.current?.isConnected) {
            event.preventDefault();
            returnFocusRef.current.focus();
          }
        }}
      >
        <SheetHeader className="shrink-0 border-b pr-10">
          <SheetTitle>Fontes da resposta</SheetTitle>
          <SheetDescription>
            Confira o documento, a apresentação e o trecho de cada referência citada.
          </SheetDescription>
        </SheetHeader>
        <ol
          className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4"
          aria-label="Trechos recuperados da bula"
        >
          {sourceChunks.map((sourceChunk, index) => (
            <li
              key={`${sourceChunk.section_title}-${index}`}
              id={messageId ? buildSourceChunkId(messageId, index + 1) : undefined}
              tabIndex={-1}
              aria-label={`Referência ${index + 1}`}
              className={cn(
                "bg-muted/40 border-border focus:ring-primary scroll-mt-4 rounded-md border p-4 outline-none focus:ring-2",
                index + 1 === selectedCitation && "border-primary"
              )}
            >
              <p className="text-foreground text-xs font-semibold">
                <span>[{index + 1}] </span>
                <span>{sourceChunk.section_title || "Seção da bula"}</span>
              </p>
              {sourceChunk.drug_name ? (
                <div className="my-2 space-y-1 text-xs">
                  {sourceChunk.corpus === "shared" && (
                    <p className="text-muted-foreground">
                      Bula compartilhada · conferência documental
                    </p>
                  )}
                  <p className="font-semibold">{sourceChunk.drug_name}</p>
                  <p>
                    {[sourceChunk.manufacturer, sourceChunk.presentation, sourceChunk.strength]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                  {getSourceLink(sourceChunk.source_url) ? (
                    <a
                      href={getSourceLink(sourceChunk.source_url)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline"
                    >
                      Abrir fonte original
                    </a>
                  ) : null}
                </div>
              ) : null}
              <Suspense
                fallback={
                  <div
                    role="status"
                    aria-label="Formatando trecho da bula"
                    className="mt-3 space-y-2"
                  >
                    <Skeleton className="h-3 w-full" />
                    <Skeleton className="h-3 w-4/5" />
                    <Skeleton className="h-3 w-3/5" />
                  </div>
                }
              >
                <MessageMarkdown
                  markdown={sourceChunk.chunk_text}
                  sectionTitle={sourceChunk.section_title}
                  variant="source"
                />
              </Suspense>
            </li>
          ))}
        </ol>
      </SheetContent>
    </Sheet>
  );
}
