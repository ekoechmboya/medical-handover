import { ClipboardList, TriangleAlert } from "lucide-react";

import BrandMark from "@/components/layout/BrandMark";
import { DecisionBadge } from "@/components/findings/DecisionBadge";
import type { FinalHandoverData } from "@/lib/finalHandover";
import { statusWord } from "@/lib/finalHandover";
import { cn } from "@/lib/cn";

function DocField({ label, value }: { label: string; value?: unknown }) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <div>
      <dt className="text-[10px] font-semibold uppercase tracking-wider text-faint">
        {label}
      </dt>
      <dd className="mt-0.5 text-sm font-medium text-ink">{String(value)}</dd>
    </div>
  );
}

export function HandoverDocument({
  data,
  standalone = false,
}: {
  data: FinalHandoverData;
  standalone?: boolean;
}) {
  const { analysis, items, rejected, pending } = data;
  const profile = analysis.patient_profile ?? {};
  const decided = analysis.findings.reduce(
    (count, finding) => count + (finding.review !== null ? 1 : 0),
    0,
  );

  return (
    <div
      className={cn(
        "w-full rounded-2xl border border-line bg-white print:rounded-none print:border-0 print:bg-white",
        standalone ? "print:shadow-none" : "shadow-[0_1px_3px_rgba(16,24,40,0.06)] print:shadow-none",
      )}
    >
      <div className="border-b border-line px-6 py-5 sm:px-8 print:border-slate-300 print:px-0 print:pt-0">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-brand-700">
              Final handover
            </p>
            <h2 className="mt-0.5 text-lg font-semibold tracking-tight">
              Handover for receiving clinician
            </h2>
          </div>
          <div className="hidden shrink-0 sm:block">
            <BrandMark className="h-8 w-8 text-brand-700" />
          </div>
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2.5 sm:grid-cols-3">
          <DocField label="Patient ID" value={profile.patient_id} />
          <DocField
            label="Age / Sex"
            value={
              profile.age != null
                ? `${profile.age} years · ${profile.sex ?? "–"}`
                : profile.sex
            }
          />
          <DocField label="Admission date" value={profile.admission_date} />
          <DocField label="Reason for admission" value={profile.admission_reason} />
          <DocField label="Current location" value={profile.current_location} />
          <DocField label="Difficulty" value={profile.difficulty} />
        </dl>
      </div>

      <div className="space-y-6 px-6 py-6 sm:px-8 print:px-0 print:py-5">
        <section>
          <div className="flex items-center gap-2">
            <ClipboardList className="h-4 w-4 text-muted print:hidden" aria-hidden="true" />
            <h3 className="text-sm font-semibold tracking-tight">Handover</h3>
          </div>
          <p className="mt-2 whitespace-pre-wrap rounded-xl border border-line bg-background px-4 py-3 font-mono text-sm leading-relaxed text-ink-soft print:rounded-none print:border-0 print:bg-transparent print:p-0 print:font-sans print:text-[13px] print:text-ink">
            {analysis.handover.trim()}
          </p>
        </section>

        {items.length > 0 ? (
          <section>
            <div className="flex items-center gap-2">
              <TriangleAlert className="h-4 w-4 text-amber-600 print:hidden" aria-hidden="true" />
              <h3 className="text-sm font-semibold tracking-tight">
                Clinically important items to address
              </h3>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-muted print:text-ink-soft">
              Approved by a clinical reviewer from the AI quality analysis.{" "}
              {items.length} item{items.length === 1 ? "" : "s"} added to the handover.
            </p>
            <ol className="mt-3 space-y-3">
              {items.map((item, index) => (
                <li
                  key={item.findingId}
                  className="flex gap-3 rounded-xl border border-line bg-background p-4 print:rounded-none print:border-slate-300 print:bg-white print:p-3"
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-800">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
                      <span className="text-sm font-semibold text-ink">
                        {item.categoryLabel}
                      </span>
                      <DecisionBadge decision={item.decision} />
                      <span className="text-[11px] text-muted">
                        {item.importance} · {statusWord(item.status)}
                      </span>
                    </div>
                    <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">
                      {item.summary}
                    </p>
                    {item.comment ? (
                      <p className="mt-1.5 text-xs italic leading-relaxed text-muted">
                        Reviewer: {item.comment}
                      </p>
                    ) : null}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        ) : null}
      </div>

      <div className="border-t border-line px-6 py-4 sm:px-8 print:border-slate-300 print:px-0 print:pb-0">
        <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] leading-relaxed text-muted">
          <p>
            {decided} finding{decided === 1 ? "" : "s"} decided · {rejected} rejected
            and excluded · {pending} pending
          </p>
          <p>
            Handover generated on{" "}
            {new Date().toLocaleDateString("en-GB", {
              day: "2-digit",
              month: "short",
              year: "numeric",
            })}
          </p>
        </div>
        <p className="mt-2 border-t border-line pt-2 text-[11px] leading-relaxed text-muted print:border-slate-300">
          This document appends clinician-approved items to the original handover. It is
          a quality-review aid built on synthetic demonstration data and must always be
          verified against source records and clinical judgment.
        </p>
      </div>
    </div>
  );
}