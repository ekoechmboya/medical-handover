import { Check, CircleAlert, Clock, FileText, Scale } from "lucide-react";

import type { ReviewSummary as ReviewSummaryData } from "@/types/api";
import { cn } from "@/lib/cn";

const SEGMENTS = [
  { key: "accepted", label: "Accepted", icon: Check, color: "bg-emerald-500", text: "text-emerald-700", ring: "hover:border-emerald-300" },
  { key: "rejected", label: "Rejected", icon: CircleAlert, color: "bg-rose-500", text: "text-rose-700", ring: "hover:border-rose-300" },
  { key: "edited", label: "Edited", icon: Scale, color: "bg-violet-500", text: "text-violet-700", ring: "hover:border-violet-300" },
  { key: "pending", label: "Pending", icon: Clock, color: "bg-slate-300", text: "text-slate-600", ring: "hover:border-slate-300" },
] as const;

export function ReviewSummaryPanel({
  summary,
  className,
}: {
  summary: ReviewSummaryData;
  className?: string;
}) {
  const segments = SEGMENTS.map((seg) => ({ ...seg, count: summary[seg.key] }));

  return (
    <div className={cn("rounded-xl border border-line bg-surface p-4", className)}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted" aria-hidden="true" />
          <h3 className="text-sm font-semibold tracking-tight">Review progress</h3>
        </div>
        <span className="text-xs text-muted">
          {summary.total} finding{summary.total === 1 ? "" : "s"}
        </span>
      </div>

      <div
        className="mt-3 flex h-2.5 w-full overflow-hidden rounded-full bg-slate-100"
        role="img"
        aria-label={`${summary.accepted} accepted, ${summary.rejected} rejected, ${summary.edited} edited, ${summary.pending} pending of ${summary.total}`}
      >
        {segments.map((seg) =>
          seg.count > 0 ? (
            <div
              key={seg.key}
              className={cn("h-full", seg.color)}
              style={{ width: `${(seg.count / Math.max(1, summary.total)) * 100}%` }}
            />
          ) : null,
        )}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="col-span-2 grid grid-cols-2 items-center gap-2">
          {segments.map((seg) => {
            const Icon = seg.icon;
            return (
              <div
                key={seg.key}
                className={cn(
                  "flex items-center gap-2 rounded-lg border border-line bg-white px-2.5 py-2",
                )}
              >
                <Icon className="h-3.5 w-3.5 shrink-0 text-muted" aria-hidden="true" />
                <div className="min-w-0">
                  <p className={cn("text-base font-semibold leading-none", seg.text)}>
                    {seg.count}
                  </p>
                  <p className="mt-0.5 truncate text-[11px] leading-none text-muted">
                    {seg.label}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {summary.total === 0 ? (
        <p className="mt-3 text-xs text-muted">No findings yet — progress appears after analysis.</p>
      ) : null}
    </div>
  );
}