"use client";

export function TypingIndicator() {
  return (
    <div className="flex gap-3 sm:gap-4">
      <div className="bg-primary/10 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full sm:h-8 sm:w-8">
        <span className="text-primary text-[10px] font-semibold sm:text-xs">AI</span>
      </div>
      <div className="bg-card border-border rounded-lg border px-4 py-3">
        <div className="flex items-center gap-1.5">
          <span className="bg-primary/60 h-2 w-2 animate-bounce rounded-full [animation-delay:0ms]" />
          <span className="bg-primary/60 h-2 w-2 animate-bounce rounded-full [animation-delay:150ms]" />
          <span className="bg-primary/60 h-2 w-2 animate-bounce rounded-full [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}
