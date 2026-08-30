/**
 * Domain vocabulary shared across the UI: canonical categories, importance and
 * status levels, human-review decisions, pipeline stages and the synthetic demo
 * scenario. Mirrors `src/medical_handover/schema.py` and the API contract.
 */

import type { ComponentType } from "react";
import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  Check,
  CircleOff,
  CircleDot,
  Clock,
  FileSearch,
  FlaskConical,
  HeartPulse,
  ListChecks,
  Minus,
  Pill,
  Scale,
  ShieldAlert,
  Stethoscope,
  Syringe,
  TriangleAlert,
  UserRound,
  type LucideProps,
} from "lucide-react";

import type { Tone } from "@/components/ui/tone";
import type { Importance, ReviewDecision } from "@/types/api";

export type IconComponent = ComponentType<LucideProps>;

export const CATEGORY_DEFS: Record<
  string,
  { label: string; icon: IconComponent; tone: Tone }
> = {
  allergy_or_adverse_reaction: {
    label: "Allergy / Adverse reaction",
    icon: ShieldAlert,
    tone: "amber",
  },
  medication: { label: "Medication", icon: Pill, tone: "sky" },
  monitoring: { label: "Monitoring", icon: HeartPulse, tone: "emerald" },
  pending_result: { label: "Pending result", icon: FlaskConical, tone: "violet" },
  escalation: { label: "Escalation", icon: TriangleAlert, tone: "rose" },
  pending_consult: { label: "Pending consult", icon: Stethoscope, tone: "indigo" },
  procedure: { label: "Procedure", icon: Syringe, tone: "cyan" },
  safety: { label: "Safety", icon: ShieldAlert, tone: "orange" },
  pending_investigation: { label: "Pending investigation", icon: FileSearch, tone: "teal" },
  clinical_status: { label: "Clinical status", icon: HeartPulse, tone: "blue" },
};

export function categoryDef(category: string) {
  return CATEGORY_DEFS[category] ?? {
    label: category.replaceAll("_", " "),
    icon: FileSearch,
    tone: "slate",
  };
}

export const IMPORTANCE_DEFS: Record<Importance, { label: string; icon: IconComponent; tone: Tone }> = {
  critical: { label: "Critical", icon: TriangleAlert, tone: "rose" },
  high: { label: "High", icon: ArrowUp, tone: "amber" },
  medium: { label: "Medium", icon: Minus, tone: "sky" },
  low: { label: "Low", icon: ArrowDown, tone: "slate" },
};

export const IMPORTANCE_LEVELS: Importance[] = ["critical", "high", "medium", "low"];

export const STATUS_DEFS: Record<
  string,
  { label: string; icon: IconComponent; tone: Tone; hint: string }
> = {
  omitted: {
    label: "Omitted",
    icon: CircleOff,
    tone: "amber",
    hint: "Not present in the handover",
  },
  partially_omitted: {
    label: "Partially omitted",
    icon: CircleDot,
    tone: "orange",
    hint: "Present but incomplete",
  },
};

export const FINDING_STATUSES = ["omitted", "partially_omitted"] as const;

export const DECISION_DEFS: Record<
  ReviewDecision | "pending",
  { label: string; icon: IconComponent; tone: Tone }
> = {
  accepted: { label: "Accepted", icon: Check, tone: "emerald" },
  rejected: { label: "Rejected", icon: AlertTriangle, tone: "rose" },
  edited: { label: "Edited", icon: Scale, tone: "violet" },
  pending: { label: "Pending review", icon: Clock, tone: "slate" },
};

export interface PipelineStageDef {
  key: string;
  short: string;
  label: string;
  description: string;
  icon: IconComponent;
}

/** Advanced agent: generate -> verify -> detail probe -> reconcile -> dedup. */
export const ADVANCED_STAGES: PipelineStageDef[] = [
  {
    key: "generate",
    short: "Generate",
    label: "Generate",
    description: "One-pass scan of the records for clinically important omissions.",
    icon: ListChecks,
  },
  {
    key: "verify",
    short: "Verify",
    label: "Verify",
    description: "Each candidate is checked against the source records; unsupported claims are dropped.",
    icon: Check,
  },
  {
    key: "detail",
    short: "Detail",
    label: "Detail probe",
    description: "Probes critical areas for omitted or under-specified detail.",
    icon: FileSearch,
  },
  {
    key: "reconcile",
    short: "Reconcile",
    label: "Reconcile",
    description: "Reconciles coverage and status against the handover text.",
    icon: ListChecks,
  },
  {
    key: "dedup",
    short: "Dedup",
    label: "Deduplicate",
    description: "Removes redundant or overlapping findings.",
    icon: CircleOff,
  },
];

export const BASELINE_STAGES: PipelineStageDef[] = [
  {
    key: "generate",
    short: "Generate",
    label: "Generate",
    description: "Single-pass AI analysis of the clinical records.",
    icon: ListChecks,
  },
];

export function stagesForMode(mode: "baseline" | "advanced"): PipelineStageDef[] {
  return mode === "advanced" ? ADVANCED_STAGES : BASELINE_STAGES;
}

export const REFERENCE_GUARD = "Gavel";
export const REVIEWER_ICON = UserRound;

/** Human-review capability list shown across the app. */
export const OVERSIGHT_CAPABILITIES = [
  { label: "Accept findings", icon: Check as IconComponent },
  { label: "Reject findings", icon: AlertTriangle as IconComponent },
  { label: "Edit findings", icon: Scale as IconComponent },
] as const;

export const ENGINE_BACKEND_LABEL: Record<string, string> = {
  mock: "Deterministic mock engine",
  gemini: "Gemini (live model)",
};