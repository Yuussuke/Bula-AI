import { ChevronDown, FileText } from "lucide-react";
import { lazy, type ReactElement, Suspense, useState } from "react";

import type { SourceChunkResponse } from "@/api/chat";
import { buildSourceChunkId } from "@/components/chat/source-chunk-navigation";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const MessageMarkdown = lazy(() => import("@/components/chat/message-markdown"));

interface SourceChunksProps {
  sourceChunks: SourceChunkResponse[];
  messageId?: string;
  isOpen?: boolean;
  onOpenChange?: (isOpen: boolean) => void;
}

export function SourceChunks({
  sourceChunks,
  messageId,
  isOpen: controlledIsOpen,
  onOpenChange,
}: SourceChunksProps): ReactElement | null {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const isOpen = controlledIsOpen ?? internalIsOpen;

  const handleOpenChange = (nextIsOpen: boolean): void => {
    setInternalIsOpen(nextIsOpen);
    onOpenChange?.(nextIsOpen);
  };

  if (sourceChunks.length === 0) {
    return null;
  }

  const sourceLabel = sourceChunks.length === 1 ? "1 fonte" : `${sourceChunks.length} fontes`;

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={handleOpenChange}
      className="border-border border-t pt-2"
    >
      <CollapsibleTrigger asChild>
        <Button type="button" variant="ghost" size="sm" className="h-8 gap-1.5 px-2 text-xs">
          <FileText aria-hidden="true" className="h-3.5 w-3.5" />
          Ver {sourceLabel} na bula
          <ChevronDown
            aria-hidden="true"
            className={cn("h-3.5 w-3.5 transition-transform", isOpen && "rotate-180")}
          />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <ol className="mt-2 space-y-2" aria-label="Trechos recuperados da bula">
          {sourceChunks.map((sourceChunk, index) => (
            <li
              key={`${sourceChunk.section_title}-${index}`}
              id={messageId ? buildSourceChunkId(messageId, index + 1) : undefined}
              tabIndex={-1}
              className="bg-muted/40 border-border focus:ring-primary scroll-mt-6 rounded-md border p-3 transition outline-none focus:ring-2"
            >
              <p className="text-foreground text-xs font-semibold">
                {sourceChunk.section_title || "Seção da bula"}
              </p>
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
      </CollapsibleContent>
    </Collapsible>
  );
}
