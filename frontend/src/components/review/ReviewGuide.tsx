import { Check, CircleAlert, Lock, Scale, UserRound } from "lucide-react";

export function ReviewGuide() {
  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-line bg-surface p-4">
        <div className="flex items-center gap-2">
          <UserRound className="h-4 w-4 text-violet-600" aria-hidden="true" />
          <h3 className="text-sm font-semibold tracking-tight">Human review</h3>
        </div>
        <ul className="mt-3 space-y-2.5">
          <li className="flex gap-2.5 text-sm text-ink-soft">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
            <span>
              <span className="font-semibold text-ink">Accept</span> — the finding
              is correct and should stand.
            </span>
          </li>
          <li className="flex gap-2.5 text-sm text-ink-soft">
            <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" aria-hidden="true" />
            <span>
              <span className="font-semibold text-ink">Reject</span> — the finding
              is not useful or not supported.
            </span>
          </li>
          <li className="flex gap-2.5 text-sm text-ink-soft">
            <Scale className="mt-0.5 h-4 w-4 shrink-0 text-violet-600" aria-hidden="true" />
            <span>
              <span className="font-semibold text-ink">Edit</span> — revise the
              wording a reviewer will carry forward.
            </span>
          </li>
        </ul>
        <div className="mt-3.5 flex items-start gap-2 rounded-lg border border-violet-200 bg-violet-50/70 px-3 py-2.5">
          <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-600" aria-hidden="true" />
          <p className="text-xs leading-relaxed text-violet-900">
            The original AI output is always preserved. Human decisions are stored
            separately and never overwrite it.
          </p>
        </div>
      </section>
    </div>
  );
}