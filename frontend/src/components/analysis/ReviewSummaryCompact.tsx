import type { ReviewSummary as ReviewSummaryData } from "@/types/api";
import { cn } from "@/lib/cn";

export function ReviewSummaryCompact({
  summary,
  className,
}: {
  summary: ReviewSummaryData;
  className?: string;
}) {
  const decided = summary.accepted + summary.rejected + summary.edited;
  const segments = [
    { count: summary.accepted, color: "bg-emerald-500" },
    { count: summary.rejected, color: "bg-rose-500" },
    { count: summary.edited, color: "bg-violet-500" },
    { count: summary.pending, color: "bg-slate-300" },
  ];

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <span className="shrink-0 text-sm font-medium text-ink-soft">Review progress</span>
      <div
        className="flex h-2 flex-1 overflow-hidden rounded-full bg-slate-100"
        role="img"
        aria-label={`${decided} of ${summary.total} findings reviewed`}
      >
        {segments.map((seg, i) =>
          seg.count > 0 ? (
            <div
              key={i}
              className={cn("h-full", seg.color)}
              style={{ width: `${(seg.count / Math.max(1, summary.total)) * 100}%` }}
            />
          ) : null,
        )}
      </div>
      <span className="shrink-0 text-xs tabular-nums text-muted">
        {decided}/{summary.total} reviewed
      </span>
    </div>
  );
}