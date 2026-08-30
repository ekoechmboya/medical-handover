import { ChevronDown, FileText } from "lucide-react";

import type { AnalysisDetail } from "@/types/api";
import { cn } from "@/lib/cn";

function Field({ label, value }: { label: string; value?: unknown }) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <div>
      <dt className="text-[11px] font-medium uppercase tracking-wide text-faint">
        {label}
      </dt>
      <dd className="mt-0.5 text-sm font-medium text-ink-soft">{String(value)}</dd>
    </div>
  );
}

export function PatientPanel({ analysis }: { analysis: AnalysisDetail }) {
  const profile = analysis.patient_profile ?? {};

  const handoverChars = analysis.handover?.length ?? 0;

  return (
    <div className="space-y-4">
      {/* Patient context */}
      <section className="rounded-xl border border-line bg-surface p-4">
        <h3 className="text-sm font-semibold tracking-tight">Patient context</h3>
        <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-3">
          <Field label="Patient ID" value={profile.patient_id} />
          <Field label="Age / Sex" value={profile.age != null ? `${profile.age} · ${profile.sex ?? "–"}` : profile.sex} />
          <Field label="Admission reason" value={profile.admission_reason} />
          <Field label="Current location" value={profile.current_location} />
          <Field label="Difficulty" value={profile.difficulty} />
          <Field label="Case" value={profile.case_id} />
        </dl>
        {profile.title ? (
          <p className="mt-3 border-t border-line pt-3 text-xs leading-relaxed text-muted">
            {String(profile.title)}
          </p>
        ) : null}
      </section>

      {/* Source records */}
      <section className="rounded-xl border border-line bg-surface">
        <div className="px-4 py-3">
          <h3 className="text-sm font-semibold tracking-tight">
            Source records{" "}
            <span className="font-normal text-muted">({analysis.records.length})</span>
          </h3>
        </div>
        <div className="border-t border-line">
          {analysis.records.map((record) => (
            <details key={record.filename} className="group border-b border-line last:border-b-0">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3 transition hover:bg-background [&::-webkit-details-marker]:hidden">
                <span className="flex min-w-0 items-center gap-2">
                  <FileText className="h-3.5 w-3.5 shrink-0 text-muted" aria-hidden="true" />
                  <span className="truncate font-mono text-xs font-medium text-ink-soft">
                    {record.filename}
                  </span>
                </span>
                <ChevronDown
                  className="h-4 w-4 shrink-0 text-muted transition-transform group-open:rotate-180"
                  aria-hidden="true"
                />
              </summary>
              <pre className="max-h-64 overflow-y-auto whitespace-pre-wrap break-words px-4 pb-4 font-mono text-xs leading-relaxed text-ink-soft scrollbars-thin">
                {record.content}
              </pre>
            </details>
          ))}
        </div>
      </section>

      {/* Current handover */}
      <section className="rounded-xl border border-line bg-surface p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold tracking-tight">Current handover</h3>
          <span className="text-[11px] text-muted">{handoverChars} chars</span>
        </div>
        <div
          className={cn(
            "scrollbars-thin mt-3 overflow-y-auto rounded-lg border border-line bg-background px-3 py-2.5",
            handoverChars > 400 ? "max-h-56" : "",
          )}
        >
          <p className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-ink-soft">
            {analysis.handover}
          </p>
        </div>
        <p className="mt-2.5 text-[11px] leading-relaxed text-muted">
          The handover is what the receiving clinician actually sees. Findings
          compare it against the records above.
        </p>
      </section>
    </div>
  );
}