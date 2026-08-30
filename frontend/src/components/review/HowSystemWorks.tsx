import { Check, Cpu, Lock, ShieldCheck, Sparkles, UserRound } from "lucide-react";

import { AgentPipeline } from "@/components/pipeline/AgentPipeline";
import { OVERSIGHT_CAPABILITIES } from "@/lib/constants";

/**
 * "How the system works" reviewer panel — the compact architecture explainer
 * used on the landing page and alongside the review workspace.
 */
export function HowSystemWorks({ compact = false }: { compact?: boolean }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <h3 className="text-base font-semibold tracking-tight">How the system works</h3>

      <div className="mt-4 space-y-5">
        {/* Baseline */}
        <div>
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-slate-600" aria-hidden="true" />
            <span className="text-sm font-semibold text-ink">Baseline</span>
          </div>
          <p className="mt-1 text-xs leading-relaxed text-muted">
            One-shot Gemini analysis — a useful point of comparison.
          </p>
        </div>

        <div className="flex items-center justify-center text-faint" aria-hidden="true">
          <span className="h-px w-full bg-line" />
        </div>

        {/* Advanced agent */}
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-brand-600" aria-hidden="true" />
            <span className="text-sm font-semibold text-ink">Advanced Agent</span>
          </div>
          <div className="mt-2.5">
            <AgentPipeline
              stages={["generate", "verify", "detail", "reconcile", "dedup"]}
              compact={compact}
            />
          </div>
          <p className="mt-2 text-xs leading-relaxed text-muted">
            Advanced findings are evidence-backed — every finding cites the source
            records it came from.
          </p>
        </div>

        <div className="flex items-center justify-center text-faint" aria-hidden="true">
          <span className="h-px w-full bg-line" />
        </div>

        {/* Human review */}
        <div>
          <div className="flex items-center gap-2">
            <UserRound className="h-4 w-4 text-violet-600" aria-hidden="true" />
            <span className="text-sm font-semibold text-ink">Human review</span>
          </div>
          <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
            {OVERSIGHT_CAPABILITIES.map((cap) => {
              const Icon = cap.icon;
              return (
                <span
                  key={cap.label}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-background px-2.5 py-1.5 text-xs font-medium text-ink-soft"
                >
                  <Icon className="h-3.5 w-3.5 text-violet-600" aria-hidden="true" />
                  {cap.label}
                </span>
              );
            })}
          </div>
        </div>
      </div>

      <div className="mt-5 space-y-2 border-t border-line pt-4">
        <p className="flex items-start gap-2 text-xs leading-relaxed text-muted">
          <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand-600" aria-hidden="true" />
          The system does not autonomously perform clinical actions.
        </p>
        <p className="flex items-start gap-2 text-xs leading-relaxed text-muted">
          <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-600" aria-hidden="true" />
          Human review is the final checkpoint for every finding.
        </p>
        <p className="flex items-start gap-2 text-xs leading-relaxed text-muted">
          <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" aria-hidden="true" />
          Demo data is synthetic. Not clinically validated.
        </p>
      </div>
    </div>
  );
}