import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import type { Tone } from "@/components/ui/tone";
import { TONE_BADGE, TONE_DOT } from "@/components/ui/tone";

interface BadgeProps {
  children: ReactNode;
  tone?: Tone;
  icon?: ReactNode;
  dot?: boolean;
  className?: string;
  title?: string;
}

export function Badge({
  children,
  tone = "slate",
  icon,
  dot,
  className,
  title,
}: BadgeProps) {
  return (
    <span
      title={title}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        TONE_BADGE[tone],
        className,
      )}
    >
      {icon ? (
        <span className="shrink-0 [&>svg]:h-3.5 [&>svg]:w-3.5">{icon}</span>
      ) : dot ? (
        <span
          aria-hidden="true"
          className={cn("h-1.5 w-1.5 shrink-0 rounded-full", TONE_DOT[tone])}
        />
      ) : null}
      {children}
    </span>
  );
}