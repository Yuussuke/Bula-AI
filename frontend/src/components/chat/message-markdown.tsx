import type { ReactElement } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

interface MessageMarkdownProps {
  markdown: string;
  variant: "answer" | "source";
  sectionTitle?: string;
  citationCount?: number;
  onCitationClick?: (citationNumber: number) => void;
}

function normalizeHeading(value: string): string {
  return value.replace(/\s+/g, " ").trim().toLocaleLowerCase("pt-BR");
}

function removeDuplicateLeadingHeading(markdown: string, sectionTitle?: string): string {
  if (!sectionTitle) {
    return markdown;
  }

  const markdownLines = markdown.split(/\r?\n/);
  const firstLine = markdownLines[0]?.trim() ?? "";
  const leadingHeadingMatch = /^#{1,6}\s+(.+?)\s*#*$/.exec(firstLine);

  if (!leadingHeadingMatch) {
    return markdown;
  }

  const headingText = leadingHeadingMatch[1];
  if (normalizeHeading(headingText) !== normalizeHeading(sectionTitle)) {
    return markdown;
  }

  return markdownLines.slice(1).join("\n").trimStart();
}

function normalizeEmphasisSpacing(markdown: string): string {
  return markdown
    .replace(/\*\*\s+([^*\n]+?)\s+\*\*/g, "**$1**")
    .replace(/__\s+([^_\n]+?)\s+__/g, "__$1__");
}

function preserveSpacingBeforeEmphasis(markdown: string): string {
  return markdown.replace(/(\S)[ \t]+(?=(?:\*\*|__)\S)/g, "$1\u00a0");
}

function linkNumericCitations(markdown: string, citationCount: number): string {
  const markdownWithCitationLinks = markdown.replace(
    /\[(\d+)\](?!\()/g,
    (citation, rawCitationNumber: string) => {
      const citationNumber = Number(rawCitationNumber);
      if (citationNumber < 1 || citationNumber > citationCount) {
        return citation;
      }

      return `[${citationNumber}](#bula-source-${citationNumber})`;
    }
  );

  return markdownWithCitationLinks.replace(/[ \t]+(?=\[\d+\]\(#bula-source-\d+\))/g, "");
}

export default function MessageMarkdown({
  markdown,
  variant,
  sectionTitle,
  citationCount = 0,
  onCitationClick,
}: MessageMarkdownProps): ReactElement {
  const visibleMarkdown = linkNumericCitations(
    preserveSpacingBeforeEmphasis(
      normalizeEmphasisSpacing(removeDuplicateLeadingHeading(markdown, sectionTitle))
    ),
    citationCount
  );

  return (
    <div
      className={cn(
        "[&_a]:text-primary overflow-x-auto leading-relaxed [&_a]:underline [&_blockquote]:border-l-2 [&_blockquote]:pl-3 [&_code]:rounded [&_code]:bg-black/5 [&_code]:px-1 [&_h1]:mt-3 [&_h1]:font-semibold [&_h2]:mt-3 [&_h2]:font-semibold [&_h3]:mt-3 [&_h3]:font-semibold [&_h4]:mt-3 [&_h4]:font-semibold [&_h5]:mt-3 [&_h5]:font-semibold [&_h6]:mt-3 [&_h6]:font-semibold [&_li]:my-1 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-2 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 [&_strong]:font-semibold [&_table]:my-3 [&_table]:w-full [&_table]:border-collapse [&_td]:border [&_td]:p-2 [&_th]:border [&_th]:bg-black/5 [&_th]:p-2 [&_th]:text-left [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5",
        variant === "source" && "text-muted-foreground mt-2 text-xs",
        variant === "answer" && "text-sm"
      )}
    >
      <Markdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={{
          a: ({ href, children }) => {
            const citationMatch = /^#bula-source-(\d+)$/.exec(href ?? "");
            if (!citationMatch || !onCitationClick) {
              return <a href={href}>{children}</a>;
            }

            const citationNumber = Number(citationMatch[1]);
            return (
              <sup className="align-super text-[0.7em] leading-none">
                <a
                  href={href}
                  aria-label={`Ir para a fonte ${citationNumber}`}
                  className="text-primary font-semibold no-underline hover:underline"
                  onClick={(event) => {
                    event.preventDefault();
                    onCitationClick(citationNumber);
                  }}
                >
                  {children}
                </a>
              </sup>
            );
          },
        }}
      >
        {visibleMarkdown}
      </Markdown>
    </div>
  );
}
