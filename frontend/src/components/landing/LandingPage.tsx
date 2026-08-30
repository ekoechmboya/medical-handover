"use client";

import { motion } from "framer-motion";
import {
  ArrowDown,
  ArrowRight,
  ClipboardCheck,
  Cpu,
  FileSearch,
  FolderOpen,
  HeartHandshake,
  ListTodo,
  ScrollText,
  ShieldCheck,
  Sparkles,
  UserRoundCheck,
} from "lucide-react";

import { Button } from "@/components/ui/Button";
import { AgentPipeline } from "@/components/pipeline/AgentPipeline";
import { HowSystemWorks } from "@/components/review/HowSystemWorks";
import { OVERSIGHT_CAPABILITIES } from "@/lib/constants";

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-40px" },
  transition: { duration: 0.45, ease: [0.4, 0, 0.2, 1] as const },
};

const WORKFLOW_STEPS = [
  {
    icon: FolderOpen,
    title: "Clinical Records",
    caption: "Admission, progress and medication notes",
  },
  {
    icon: Sparkles,
    title: "AI Analysis",
    caption: "Agentic pipeline scans for omissions",
  },
  {
    icon: FileSearch,
    title: "Evidence Retrieval",
    caption: "Every finding is linked to a source",
  },
  {
    icon: ShieldCheck,
    title: "Verification",
    caption: "Claims are checked before surfacing",
  },
  {
    icon: UserRoundCheck,
    title: "Human Review",
    caption: "A qualified reviewer makes the call",
  },
];

export function LandingPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      {/* ------------------------------------------------------------------ */}
      {/* Hero */}
      {/* ------------------------------------------------------------------ */}
      <section className="pb-16 pt-16 sm:pb-24 sm:pt-24">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
          className="mx-auto max-w-3xl text-center"
        >
          <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-800">
            <HeartHandshake className="h-3.5 w-3.5" aria-hidden="true" />
            Clinical handover review · human-in-the-loop
          </span>
          <h1 className="mt-6 text-balance text-4xl font-semibold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
            Medical Handover{" "}
            <span className="text-brand-700">Quality Agent</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-balance text-base leading-relaxed text-muted sm:text-lg">
            An agentic AI system that identifies potentially missing or
            incomplete information in clinical handovers, verifies its findings
            against source records, and keeps qualified humans in control.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button href="/workspace" size="lg">
              <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
              Open Analysis Workspace
            </Button>
            <Button href="/analyses" size="lg" variant="secondary">
              View analysis history
            </Button>
          </div>
          <p className="mt-5 text-xs text-faint">
            Synthetic demonstration data · Candidate findings only · No
            autonomous clinical decisions
          </p>
        </motion.div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Workflow */}
      {/* ------------------------------------------------------------------ */}
      <section className="pb-16 sm:pb-24" aria-label="How a handover becomes a review">
        <motion.div {...fadeUp}>
          <ol className="flex flex-col items-stretch gap-2 md:flex-row md:items-center md:gap-0">
            {WORKFLOW_STEPS.map((step) => {
              const Icon = step.icon;
              return (
                <li
                  key={step.title}
                  className="flex flex-1 flex-col items-center gap-1 text-center"
                >
                  <div className="flex w-full flex-col items-center gap-2">
                    <span className="flex h-12 w-12 items-center justify-center rounded-full border border-line bg-white text-brand-700 shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </span>
                    <span className="text-sm font-semibold text-ink">{step.title}</span>
                    <span className="max-w-[13rem] text-[11px] leading-snug text-muted">
                      {step.caption}
                    </span>
                  </div>
                </li>
              );
            })}
          </ol>
          <div className="mt-6 flex items-center justify-center gap-2 text-xs text-faint">
            <ShieldCheck className="h-3.5 w-3.5 text-brand-600" aria-hidden="true" />
            Every finding in this chain stays a <strong className="text-ink-soft">candidate</strong> until a human decides.
          </div>
        </motion.div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Capabilities */}
      {/* ------------------------------------------------------------------ */}
      <section className="pb-16 sm:pb-24" aria-label="Capabilities">
        <motion.h2
          {...fadeUp}
          className="text-center text-2xl font-semibold tracking-tight sm:text-3xl"
        >
          Three layers, one workflow
        </motion.h2>
        <motion.p
          {...fadeUp}
          transition={{ ...fadeUp.transition, delay: 0.05 }}
          className="mx-auto mt-2 max-w-2xl text-center text-sm text-muted"
        >
          A baseline worth comparing against, an evidence-backed agent, and a
          review layer that keeps original AI output intact.
        </motion.p>

        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {/* Baseline */}
          <motion.div
            {...fadeUp}
            className="rounded-2xl border border-line bg-surface p-6"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-600">
              <Cpu className="h-5 w-5" aria-hidden="true" />
            </div>
            <h3 className="mt-4 text-base font-semibold tracking-tight">Baseline</h3>
            <ul className="mt-3 space-y-2 text-sm text-muted">
              <li className="flex gap-2">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-slate-400" aria-hidden="true" />
                Single-pass AI analysis of the records
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-slate-400" aria-hidden="true" />
                Fast and simple — a useful benchmark
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-slate-400" aria-hidden="true" />
                No retrieval, no verification step
              </li>
            </ul>
          </motion.div>

          {/* Advanced Agent */}
          <motion.div
            {...fadeUp}
            transition={{ ...fadeUp.transition, delay: 0.08 }}
            className="rounded-2xl border border-brand-200 bg-surface p-6 shadow-[0_4px_20px_rgba(20,184,166,0.08)]"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-brand-200 bg-brand-50 text-brand-700">
              <Sparkles className="h-5 w-5" aria-hidden="true" />
            </div>
            <h3 className="mt-4 text-base font-semibold tracking-tight">Advanced Agent</h3>
            <ul className="mt-3 space-y-2 text-sm text-muted">
              <li className="flex gap-2">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-brand-500" aria-hidden="true" />
                Retrieval of supporting evidence
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-brand-500" aria-hidden="true" />
                Verification of candidate findings
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-brand-500" aria-hidden="true" />
                Detail probing, reconciliation, deduplication
              </li>
            </ul>
          </motion.div>

          {/* Human Oversight */}
          <motion.div
            {...fadeUp}
            transition={{ ...fadeUp.transition, delay: 0.16 }}
            className="rounded-2xl border border-line bg-surface p-6"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-violet-200 bg-violet-50 text-violet-700">
              <UserRoundCheck className="h-5 w-5" aria-hidden="true" />
            </div>
            <h3 className="mt-4 text-base font-semibold tracking-tight">Human Oversight</h3>
            <ul className="mt-3 space-y-2 text-sm text-muted">
              {OVERSIGHT_CAPABILITIES.map((cap) => {
                const Icon = cap.icon;
                return (
                  <li key={cap.label} className="flex gap-2">
                    <Icon className="mt-0.5 h-4 w-4 shrink-0 text-violet-600" aria-hidden="true" />
                    {cap.label}
                  </li>
                );
              })}
            </ul>
            <p className="mt-3 text-xs leading-relaxed text-faint">
              Original AI output is preserved on every decision.
            </p>
          </motion.div>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Why this matters */}
      {/* ------------------------------------------------------------------ */}
      <section className="pb-16 sm:pb-24" aria-label="Why this matters">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <motion.div {...fadeUp}>
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Why this matters
            </h2>
            <p className="mt-4 max-w-xl leading-relaxed text-muted">
              Across a shift, the information that matters most travels through
              conversation, notes, and a written handover. Complex handovers are
              where critical detail is most likely to fall away — an allergy not
              recorded, an anticoagulant not mentioned, an escalation criterion
              left out.
            </p>
            <p className="mt-3 max-w-xl leading-relaxed text-muted">
              These omissions are rarely visible in the moment, yet they shape
              the decisions a receiving clinician makes. This system surfaces
              them as <span className="font-medium text-ink">candidate findings
              with evidence</span>, so the next clinician can verify and decide
              — rather than rediscover the gap later.
            </p>
          </motion.div>

          <motion.div
            {...fadeUp}
            transition={{ ...fadeUp.transition, delay: 0.08 }}
            className="rounded-2xl border border-line bg-surface p-6"
          >
            <div className="flex items-center gap-2">
              <ScrollText className="h-4 w-4 text-muted" aria-hidden="true" />
              <h3 className="text-sm font-semibold tracking-tight">
                Information lost in the handover chain
              </h3>
            </div>
            <ol className="mt-4 space-y-0">
              {[
                "Clinical records capture the full picture",
                "The handover shortens, filters, and compresses",
                "Detail drops out — silently",
                "The receiving clinician needs it most",
              ].map((text, index) => (
                <li key={text} className="relative flex items-center gap-3 pl-8 pb-4 last:pb-0">
                  {index < 3 ? (
                    <span
                      className="absolute left-[13px] top-6 h-full w-px bg-line"
                      aria-hidden="true"
                    />
                  ) : null}
                  <span className="absolute left-0 top-0.5 flex h-7 w-7 items-center justify-center rounded-full border border-line bg-background font-mono text-xs font-semibold text-muted">
                    {index + 1}
                  </span>
                  <span
                    className={`text-sm leading-relaxed ${
                      index === 3
                        ? "font-semibold text-brand-800"
                        : "text-ink-soft"
                    }`}
                  >
                    {text}
                  </span>
                </li>
              ))}
            </ol>
          </motion.div>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* How the system works */}
      {/* ------------------------------------------------------------------ */}
      <section className="pb-16 sm:pb-24" aria-label="How the system works">
        <motion.div {...fadeUp} className="mx-auto max-w-3xl">
          <HowSystemWorks />
        </motion.div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Baseline vs advanced + evaluation placeholder */}
      {/* ------------------------------------------------------------------ */}
      <section className="pb-16 sm:pb-24" aria-label="Baseline versus advanced">
        <motion.div {...fadeUp} className="grid gap-5 md:grid-cols-2">
          <div className="rounded-2xl border border-line bg-surface p-6">
            <h3 className="flex items-center gap-2 text-base font-semibold tracking-tight">
              <Cpu className="h-4 w-4 text-slate-600" aria-hidden="true" />
              Baseline mode
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              One-shot analysis: the model reads the records and emits candidate
              omissions in a single pass.
            </p>
            <div className="mt-4">
              <AgentPipeline stages={["generate"]} compact />
            </div>
          </div>
          <div className="rounded-2xl border border-brand-200 bg-surface p-6">
            <h3 className="flex items-center gap-2 text-base font-semibold tracking-tight">
              <Sparkles className="h-4 w-4 text-brand-700" aria-hidden="true" />
              Advanced Agent mode
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              A staged agent workflow that generates, then verifies and refines
              its findings against the records.
            </p>
            <div className="mt-4">
              <AgentPipeline
                stages={["generate", "verify", "detail", "reconcile", "dedup"]}
                compact
              />
            </div>
          </div>
        </motion.div>

        <motion.div
          {...fadeUp}
          className="mt-5 rounded-xl border border-dashed border-line-strong bg-white/60 px-5 py-4 text-center"
        >
          <p className="text-sm text-muted">
            The same underlying model powers both modes, so the comparison
            measures{" "}
            <span className="font-semibold text-ink-soft">
              agentic engineering, not model capability
            </span>
            . Measured benchmark results from the evaluation harness will be
            surfaced here after the experiment run.
          </p>
        </motion.div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* CTA */}
      {/* ------------------------------------------------------------------ */}
      <section className="pb-20 sm:pb-28" aria-label="Get started">
        <motion.div
          {...fadeUp}
          className="overflow-hidden rounded-2xl border border-brand-200 bg-gradient-to-br from-brand-50 via-white to-brand-50 px-6 py-14 text-center sm:px-12"
        >
          <ListTodo className="mx-auto h-8 w-8 text-brand-700" aria-hidden="true" />
          <h2 className="mt-4 text-balance text-2xl font-semibold tracking-tight sm:text-3xl">
            See a handover reviews in minutes
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted">
            Load a demo scenario, choose the mode, run the analysis, and review
            the findings as a human reviewer would. No setup, no typing piles of
            medical text.
          </p>
          <div className="mt-7 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button href="/workspace" size="lg">
              Open Analysis Workspace
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Button href="/analyses" size="lg" variant="secondary">
              <FolderOpen className="h-4 w-4" aria-hidden="true" />
              Browse analysis history
            </Button>
          </div>
          <p className="mt-6 inline-flex items-center gap-1.5 text-xs text-faint">
            <ArrowDown className="h-3 w-3" aria-hidden="true" />
            Built for the micro1 Frontier Engineering Challenge
          </p>
        </motion.div>
      </section>
    </div>
  );
}