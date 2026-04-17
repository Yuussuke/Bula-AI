"use client"

export function TypingIndicator() {
  return (
    <div className="flex gap-3 sm:gap-4">
      <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
        <span className="text-[10px] sm:text-xs font-semibold text-primary">AI</span>
      </div>
      <div className="bg-card border border-border rounded-lg px-4 py-3">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-primary/60 animate-bounce [animation-delay:0ms]" />
          <span className="w-2 h-2 rounded-full bg-primary/60 animate-bounce [animation-delay:150ms]" />
          <span className="w-2 h-2 rounded-full bg-primary/60 animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  )
}
