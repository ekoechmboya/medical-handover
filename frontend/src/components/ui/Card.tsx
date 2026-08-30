import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface CardProps {
  children: ReactNode;
  className?: string;
  padded?: boolean;
  interactive?: boolean;
}

export function Card({ children, className, padded = true, interactive }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-line bg-surface shadow-[0_1px_2px_rgba(16,24,40,0.04)]",
        padded && "p-5",
        interactive &&
          "transition-shadow hover:shadow-[0_4px_16px_rgba(16,24,40,0.08)]",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  icon,
  action,
  className,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-4 flex items-start justify-between gap-3", className)}>
      <div className="flex items-start gap-2.5">
        {icon ? (
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-line bg-background text-brand-700 [&>svg]:h-4 [&>svg]:w-4">
            {icon}
          </span>
        ) : null}
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-ink">{title}</h3>
          {subtitle ? (
            <p className="mt-0.5 text-xs leading-relaxed text-muted">{subtitle}</p>
          ) : null}
        </div>
      </div>
      {action}
    </div>
  );
}