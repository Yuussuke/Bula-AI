import { type ReactElement, useEffect, useId, useState } from "react";

import { cn } from "@/lib/utils";

interface AssistantAvatarProps {
  className?: string;
  isLoading?: boolean;
}

export function AssistantAvatar({
  className,
  isLoading = false,
}: AssistantAvatarProps): ReactElement {
  const illustrationId = useId();
  const [isHovered, setIsHovered] = useState(false);
  const [isPulsing, setIsPulsing] = useState(false);
  const [isTouchPouring, setIsTouchPouring] = useState(false);
  const isPouring = isLoading || isHovered || isTouchPouring;

  useEffect(() => {
    if (!isPulsing) return;
    const timeout = window.setTimeout(() => setIsPulsing(false), 650);
    return () => window.clearTimeout(timeout);
  }, [isPulsing]);

  useEffect(() => {
    if (!isTouchPouring) return;
    const timeout = window.setTimeout(() => setIsTouchPouring(false), 1800);
    return () => window.clearTimeout(timeout);
  }, [isTouchPouring]);

  return (
    <button
      type="button"
      aria-label={isLoading ? "Assistente preparando a resposta" : "Animar assistente Bula AI"}
      disabled={isLoading}
      data-pouring={isPouring || undefined}
      data-pulsing={isPulsing || undefined}
      data-loading={isLoading || undefined}
      onPointerEnter={(event) => {
        if (event.pointerType !== "touch" && !isLoading) setIsHovered(true);
      }}
      onPointerLeave={() => setIsHovered(false)}
      onPointerUp={(event) => {
        if (event.pointerType === "touch") setIsTouchPouring(true);
      }}
      onFocus={(event) => {
        if (event.currentTarget.matches(":focus-visible")) setIsHovered(true);
      }}
      onBlur={() => setIsHovered(false)}
      onClick={() => {
        if (!isPulsing) setIsPulsing(true);
      }}
      className={cn(
        "assistant-avatar focus-visible:outline-ring relative block h-12 w-12 shrink-0 rounded-lg border-0 bg-transparent p-0 focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-default dark:brightness-150",
        className
      )}
    >
      <svg aria-hidden="true" viewBox="0 0 1254 1254" fill="none" className="block h-full w-full">
        <defs>
          <clipPath id={`${illustrationId}-flow`} clipPathUnits="userSpaceOnUse">
            <path d="M490 430H980V820C870 846 595 846 490 819Z" />
          </clipPath>
          <linearGradient
            id={`${illustrationId}-capsule`}
            x1="250"
            y1="110"
            x2="750"
            y2="700"
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor="#027967" />
            <stop offset="1" stopColor="#027b6a" />
          </linearGradient>
          <linearGradient
            id={`${illustrationId}-particles`}
            x1="580"
            y1="510"
            x2="815"
            y2="765"
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor="#55b07d" />
            <stop offset="1" stopColor="#56b07f" />
          </linearGradient>
        </defs>
        <g className="assistant-capsule">
          <path
            fill={`url(#${illustrationId}-capsule)`}
            d="m425 701-210-213c-100-101-97-217-22-314C269 75 374 53 466 103c28 15 54 39 80 65l243 210c21 18 18 31 3 58-20 36-51 73-79 96l-7-16-17-18c32-34 72-83 68-99-8-30-122 50-181 105-58 52-153 145-133 166 10 11 39-8 80-26 0 16 4 30 13 41-45 26-84 41-111 16Z"
          />
        </g>
        <g
          className="assistant-particles"
          fill={`url(#${illustrationId}-particles)`}
          clipPath={`url(#${illustrationId}-flow)`}
        >
          <circle cx="653" cy="552" r="40" />
          <circle cx="581" cy="648" r="36" />
          <circle cx="729" cy="629" r="36" />
          <circle cx="671" cy="715" r="37" />
          <circle cx="810" cy="715" r="49" />
        </g>
        <g fill="#027b6a">
          <path
            fillRule="evenodd"
            d="M470 800c58-43 471-47 530-2 33 25 51 103 42 170-8 67-37 114-90 151l21 73c8 29-8 40-33 30-35-14-76-42-102-61H642c-105 0-184-63-207-155-19-77 4-164 35-206Zm28 19c93-28 377-28 472 1-100 26-375 27-472-1Zm-7 30c-18 43-28 98-14 146 20 70 79 121 165 123h202c8 0 14 3 21 8l52 39-12-53c-3-15 1-22 12-30 50-36 72-78 77-126 4-36-2-74-13-107-112 36-376 36-490 0Z"
            clipRule="evenodd"
          />
          <g className="assistant-face">
            <circle cx="604" cy="981" r="50" />
            <circle cx="733" cy="1002" r="35" />
            <circle cx="861" cy="982" r="50" />
          </g>
        </g>
      </svg>
    </button>
  );
}
