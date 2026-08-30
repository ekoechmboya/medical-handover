import { LoaderCircle } from "lucide-react";

import { cn } from "@/lib/cn";

export function Spinner({
  className,
  label,
}: {
  className?: string;
  label?: string;
}) {
  if (!label) {
    return (
      <LoaderCircle
        className={cn("h-5 w-5 animate-spin text-brand-700", className)}
        aria-hidden="true"
      />
    );
  }
  return (
    <span className={cn("inline-flex items-center gap-2 text-sm text-muted", className)}>
      <LoaderCircle className="h-4 w-4 animate-spin text-brand-700" aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}