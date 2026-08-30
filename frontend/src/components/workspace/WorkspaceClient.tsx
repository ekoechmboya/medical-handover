"use client";

import { useMemo, useRef, useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  Bot,
  Check,
  FilePlus2,
  FolderOpen,
  LoaderCircle,
  Plus,
  Sparkles,
  Trash2,
  Wand2,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { AgentPipeline } from "@/components/pipeline/AgentPipeline";
import { ReviewWorkspace } from "@/components/analysis/ReviewWorkspace";
import { ModeBadge } from "@/components/analysis/ModeBadge";
import { DEMO_SCENARIO } from "@/lib/demo";
import { formatElapsed } from "@/lib/format";
import { api } from "@/lib/api";

import type { AnalysisDetail, AnalysisInput, Mode, RecordItem } from "@/types/api";

interface RecordDraft {
  filename: string;
  content: string;
}

interface FormState {
  patientId: string;
  age: string;
  sex: string;
  admissionReason: string;
  currentLocation: string;
  records: RecordDraft[];
  handover: string;
  mode: Mode;
}

const INITIAL_FORM: FormState = {
  patientId: "",
  age: "",
  sex: "",
  admissionReason: "",
  currentLocation: "",
  records: [{ filename: "", content: "" }],
  handover: "",
  mode: "advanced",
};

const STEPS = [
  { id: 1, label: "Input" },
  { id: 2, label: "Analysis" },
  { id: 3, label: "Review results" },
];

export function WorkspaceClient() {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [result, setResult] = useState<AnalysisDetail | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!running) return;
    const start = performance.now();
    const interval = setInterval(() => setElapsedMs(performance.now() - start), 250);
    return () => clearInterval(interval);
  }, [running]);

  const setField = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((f) => ({ ...f, [key]: value }));
    setValidationErrors((e) => {
      if (!e[key]) return e;
      const next = { ...e };
      delete next[key];
      return next;
    });
  };

  const setRecord = (index: number, patch: Partial<RecordDraft>) => {
    setForm((f) => ({
      ...f,
      records: f.records.map((record, i) => (i === index ? { ...record, ...patch } : record)),
    }));
  };

  const loadDemo = () => {
    const demo = DEMO_SCENARIO;
    setForm({
      patientId: String(demo.patient_profile.patient_id ?? ""),
      age: demo.patient_profile.age != null ? String(demo.patient_profile.age) : "",
      sex: String(demo.patient_profile.sex ?? ""),
      admissionReason: String(demo.patient_profile.admission_reason ?? ""),
      currentLocation: String(demo.patient_profile.current_location ?? ""),
      records: demo.records.map((record: RecordItem) => ({ ...record })),
      handover: demo.handover,
      mode: form.mode,
    });
    setValidationErrors({});
  };

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    const records = form.records.filter((r) => r.filename.trim() || r.content.trim());
    if (!form.patientId.trim()) errors.patientId = "Patient ID is required.";
    if (!form.admissionReason.trim()) errors.admissionReason = "Admission reason is required.";
    if (records.length === 0) {
      errors.records = "Add at least one clinical record.";
    } else {
      const empty = records.findIndex(
        (r) => !r.filename.trim() || r.content.trim().length < 10,
      );
      if (empty >= 0) {
        errors.records = `Record #${empty + 1} needs a filename and meaningful content.`;
      }
    }
    if (form.handover.trim().length < 10) {
      errors.handover = "The current handover needs at least a short sentence.";
    }
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const buildInput = (): AnalysisInput => {
    const records = form.records
      .filter((r) => r.filename.trim() && r.content.trim())
      .map((r) => ({ filename: r.filename.trim(), content: r.content.trim() }));
    const age = Number.parseInt(form.age, 10);
    return {
      patient_profile: {
        case_id: "manual_demo",
        title: "Manual analysis",
        difficulty: "demo",
        patient_id: form.patientId.trim(),
        age: Number.isFinite(age) ? age : undefined,
        sex: form.sex || undefined,
        admission_reason: form.admissionReason.trim(),
        current_location: form.currentLocation.trim() || undefined,
      },
      records,
      handover: form.handover.trim(),
      mode: form.mode,
    };
  };

  const runAnalysis = async () => {
    if (!validate()) {
      setStep(1);
      return;
    }
    setRunning(true);
    setRunError(null);
    setElapsedMs(0);
    setStep(2);
    try {
      const analysis = await api.createAnalysis(buildInput());
      if (!mountedRef.current) return;
      setResult(analysis);
      setStep(3);
    } catch (err) {
      if (!mountedRef.current) return;
      setRunError(err instanceof Error ? err.message : "The analysis could not be run.");
      setRunning(false);
    } finally {
      if (mountedRef.current) setRunning(false);
    }
  };

  const reset = () => {
    setForm(INITIAL_FORM);
    setResult(null);
    setRunError(null);
    setElapsedMs(0);
    setValidationErrors({});
    setStep(1);
  };

  const EnginePipeline = useMemo(() => {
    return form.mode === "advanced"
      ? ["generate", "verify", "detail", "reconcile", "dedup"]
      : ["generate"];
  }, [form.mode]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
      {/* Step indicator */}
      <ol className="flex items-center justify-center gap-0 sm:gap-2" aria-label="Workflow steps">
        {STEPS.map((item, index) => {
          const current = step === item.id;
          const done = step > item.id;
          return (
            <li key={item.id} className="flex items-center gap-1 sm:gap-2">
              <span
                className={`flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-semibold sm:px-3.5 ${
                  current
                    ? "border-brand-500 bg-brand-50 text-brand-800"
                    : done
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                      : "border-line bg-white text-muted"
                }`}
              >
                <span
                  className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] ${
                    current
                      ? "bg-brand-600 text-white"
                      : done
                        ? "bg-emerald-500 text-white"
                        : "bg-slate-100 text-muted"
                  }`}
                >
                  {done ? <Check className="h-3 w-3" aria-hidden="true" /> : item.id}
                </span>
                <span className="hidden sm:inline">{item.label}</span>
              </span>
              {index < STEPS.length - 1 ? (
                <ArrowRight
                  className="h-3.5 w-3.5 text-faint"
                  aria-hidden="true"
                />
              ) : null}
            </li>
          );
        })}
      </ol>

      <div className="mt-8">
        <AnimatePresence mode="wait">
          {step === 1 ? (
            <motion.div
              key="step1"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h1 className="text-2xl font-semibold tracking-tight">
                    New analysis
                  </h1>
                  <p className="mt-1 text-sm text-muted">
                    Describe the patient, supply the records, and paste the current handover.
                  </p>
                </div>
                <Button variant="secondary" onClick={loadDemo}>
                  <Wand2 className="h-4 w-4" aria-hidden="true" />
                  Load Demo Scenario
                </Button>
              </div>

              <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
                {/* Inputs */}
                <div className="space-y-6">
                  {/* Patient context */}
                  <Card>
                    <CardHeader
                      title="Patient context"
                      subtitle="Who this handover is about."
                      icon={<FolderOpen aria-hidden="true" />}
                    />
                    <div className="grid gap-4 sm:grid-cols-2">
                      <Field
                        id="patient-id"
                        label="Patient ID"
                        value={form.patientId}
                        onChange={(v) => setField("patientId", v)}
                        placeholder="e.g. HSP-48291"
                        error={validationErrors.patientId}
                      />
                      <Field
                        id="age"
                        label="Age"
                        value={form.age}
                        onChange={(v) => setField("age", v)}
                        placeholder="e.g. 64"
                        inputMode="numeric"
                      />
                      <div>
                        <label htmlFor="sex" className="mb-1.5 block text-sm font-medium text-ink-soft">
                          Sex
                        </label>
                        <select
                          id="sex"
                          value={form.sex}
                          onChange={(e) => setField("sex", e.target.value)}
                          className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
                        >
                          <option value="">Not specified</option>
                          <option value="F">Female</option>
                          <option value="M">Male</option>
                          <option value="Other">Other</option>
                        </select>
                      </div>
                      <Field
                        id="admission-reason"
                        label="Admission reason"
                        value={form.admissionReason}
                        onChange={(v) => setField("admissionReason", v)}
                        placeholder="e.g. Community-acquired pneumonia"
                        error={validationErrors.admissionReason}
                      />
                      <Field
                        id="current-location"
                        label="Current location"
                        value={form.currentLocation}
                        onChange={(v) => setField("currentLocation", v)}
                        placeholder="e.g. Medical Ward A"
                        className="sm:col-span-2"
                      />
                    </div>
                  </Card>

                  {/* Clinical records */}
                  <Card>
                    <CardHeader
                      title="Clinical records"
                      subtitle="The evidence the agent will analyse."
                      icon={<FilePlus2 aria-hidden="true" />}
                      action={
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            setForm((f) => ({
                              ...f,
                              records: [...f.records, { filename: "", content: "" }],
                            }))
                          }
                          aria-label="Add a record"
                        >
                          <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                          Add record
                        </Button>
                      }
                    />
                    <div className="space-y-4">
                      {form.records.map((record, index) => (
                        <div
                          key={index}
                          className="rounded-xl border border-line bg-background/50 p-3.5"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="text-[11px] font-semibold uppercase tracking-wide text-muted">
                              Record #{index + 1}
                            </span>
                            {form.records.length > 1 ? (
                              <button
                                type="button"
                                onClick={() =>
                                  setForm((f) => ({
                                    ...f,
                                    records: f.records.filter((_, i) => i !== index),
                                  }))
                                }
                                className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-xs font-medium text-rose-700 transition hover:bg-rose-50"
                                aria-label={`Remove record ${index + 1}`}
                              >
                                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                                Remove
                              </button>
                            ) : null}
                          </div>
                          <label
                            htmlFor={`record-filename-${index}`}
                            className="mb-1.5 mt-3 block text-xs font-medium text-ink-soft"
                          >
                            Filename
                          </label>
                          <input
                            id={`record-filename-${index}`}
                            value={record.filename}
                            onChange={(e) => setRecord(index, { filename: e.target.value })}
                            placeholder="e.g. admission_note.txt"
                            className="w-full rounded-lg border border-line bg-white px-3 py-2 font-mono text-sm text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
                          />
                          <label
                            htmlFor={`record-content-${index}`}
                            className="mb-1.5 mt-3 block text-xs font-medium text-ink-soft"
                          >
                            Content
                          </label>
                          <textarea
                            id={`record-content-${index}`}
                            value={record.content}
                            onChange={(e) => setRecord(index, { content: e.target.value })}
                            rows={4}
                            className="w-full resize-y rounded-lg border border-line bg-white px-3 py-2 font-mono text-xs leading-relaxed text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30 scrollbars-thin"
                            placeholder="Paste the record text…"
                          />
                        </div>
                      ))}
                      {validationErrors.records ? (
                        <p className="text-xs font-medium text-rose-700" role="alert">
                          {validationErrors.records}
                        </p>
                      ) : null}
                    </div>
                    <p className="mt-4 text-[11px] leading-relaxed text-muted">
                      Records should be plain text (such as admission or progress notes).
                      Ground-truth concepts are blocked at the API boundary.
                    </p>
                  </Card>

                  {/* Current handover */}
                  <Card>
                    <CardHeader
                      title="Current handover"
                      subtitle="The note the receiving clinician would actually see."
                      icon={<Sparkles aria-hidden="true" />}
                    />
                    <textarea
                      id="handover"
                      value={form.handover}
                      onChange={(e) => setField("handover", e.target.value)}
                      rows={5}
                      className="w-full resize-y rounded-lg border border-line bg-white px-3 py-2.5 text-sm leading-relaxed text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30 scrollbars-thin"
                      placeholder="Paste the current handover note — this is what the agent checks for omissions…"
                    />
                    {validationErrors.handover ? (
                      <p className="mt-1.5 text-xs font-medium text-rose-700" role="alert">
                        {validationErrors.handover}
                      </p>
                    ) : null}
                  </Card>
                </div>

                {/* Right rail: mode + run */}
                <div className="space-y-5 lg:sticky lg:top-20 lg:self-start">
                  <Card>
                    <CardHeader
                      title="Analysis mode"
                      subtitle="Choose how the agent works."
                      icon={<Bot aria-hidden="true" />}
                    />
                    <SegmentedControl
                      name="analysis-mode"
                      value={form.mode}
                      onChange={(value) => setField("mode", value as Mode)}
                      options={[
                        {
                          value: "baseline",
                          label: "Baseline",
                          description: "Single-pass AI analysis",
                          icon: <Bot aria-hidden="true" />,
                        },
                        {
                          value: "advanced",
                          label: "Advanced Agent",
                          description: "Retrieval + verification",
                          icon: <Sparkles aria-hidden="true" />,
                        },
                      ]}
                    />
                    <div className="mt-4">
                      <AgentPipeline stages={EnginePipeline} compact />
                    </div>
                  </Card>

                  <Card padded={false}>
                    <div className="p-5">
                      <Button
                        className="w-full"
                        size="lg"
                        onClick={() => void runAnalysis()}
                      >
                        Run Analysis
                        <ArrowRight className="h-4 w-4" aria-hidden="true" />
                      </Button>
                      <p className="mt-2.5 text-center text-[11px] text-muted">
                        {form.mode === "advanced"
                          ? "Advanced mode may take a minute or two on the live model backend."
                          : "Baseline mode is usually quick."}
                      </p>
                    </div>
                    <div className="flex items-center justify-center gap-1.5 border-t border-line bg-background px-5 py-3">
                      <Wand2 className="h-3.5 w-3.5 text-faint" aria-hidden="true" />
                      <span className="text-[11px] text-faint">
                        Load Demo Scenario · Synthetic demonstration data
                      </span>
                    </div>
                  </Card>

                  <Link
                    href="/analyses"
                    className="block text-center text-xs font-medium text-muted transition hover:text-ink"
                  >
                    Already ran one? Browse analysis history →
                  </Link>
                </div>
              </div>
            </motion.div>
          ) : null}

          {step === 2 ? (
            <motion.div
              key="step2"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="mx-auto max-w-2xl"
            >
              <Card className="overflow-hidden">
                <div className="px-6 py-8 text-center">
                  <div className="relative mx-auto flex h-14 w-14 items-center justify-center">
                    <span className="absolute inset-0 animate-ping rounded-full bg-brand-200/40" aria-hidden="true" />
                    <span className="relative flex h-14 w-14 items-center justify-center rounded-full border border-brand-200 bg-brand-50">
                      <LoaderCircle className="h-6 w-6 animate-spin text-brand-700" aria-hidden="true" />
                    </span>
                  </div>
                  <div className="mt-5 flex items-center justify-center gap-2">
                    <h2 className="text-lg font-semibold tracking-tight">
                      Preparing evidence-backed analysis
                    </h2>
                    <ModeBadge mode={form.mode} size="sm" />
                  </div>
                  <p className="mx-auto mt-2 max-w-md text-sm text-muted">
                    {runError
                      ? undefined
                      : form.mode === "advanced"
                        ? "Running the agent pipeline against the source records. This may take a minute or two on the live model backend."
                        : "Running the baseline one-shot analysis against the source records."}
                  </p>

                  {runError ? (
                    <div
                      role="alert"
                      className="mx-auto mt-4 max-w-md rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-left"
                    >
                      <p className="text-sm font-semibold text-rose-800">
                        Analysis could not be completed
                      </p>
                      <p className="mt-1 text-sm leading-relaxed text-rose-900">{runError}</p>
                    </div>
                  ) : null}

                  {!runError ? (
                    <>
                      <div className="mt-5 flex items-center justify-center gap-3">
                        <div className="h-1.5 w-48 overflow-hidden rounded-full bg-slate-100">
                          <div className="bg-shimmer h-full w-full" />
                        </div>
                        <span className="text-xs tabular-nums text-muted">
                          {formatElapsed(elapsedMs)}
                        </span>
                      </div>
                      <div className="mt-6 flex justify-center">
                        <AgentPipeline stages={EnginePipeline} />
                      </div>
                      <p className="mt-6 text-[11px] text-faint">
                        The agent only produces candidate findings — no clinical
                        decisions are made autonomously. Synthetic demonstration data.
                      </p>
                    </>
                  ) : null}
                </div>
              </Card>

              <div className="mt-4 flex items-center justify-between">
                <Button variant="ghost" onClick={() => setStep(1)}>
                  <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                  Back to input
                </Button>
                {runError ? (
                  <Button onClick={() => void runAnalysis()} loading={running}>
                    Try again
                  </Button>
                ) : null}
              </div>
            </motion.div>
          ) : null}

          {step === 3 && result ? (
            <motion.div
              key="step3"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-semibold tracking-tight">
                    Review results
                  </h1>
                  <ModeBadge mode={result.mode} />
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" onClick={reset}>
                    New analysis
                  </Button>
                  <Button variant="secondary" href={`/analyses/${result.id}`}>
                    Open analysis page
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
              </div>
              <ReviewWorkspace analysis={result} />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  );
}

function Field({
  id,
  label,
  value,
  onChange,
  placeholder,
  className,
  error,
  inputMode,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  error?: string;
  inputMode?: "numeric";
}) {
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-ink-soft">
        {label}
      </label>
      <input
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        inputMode={inputMode}
        className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
      />
      {error ? (
        <p className="mt-1.5 text-xs font-medium text-rose-700" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}