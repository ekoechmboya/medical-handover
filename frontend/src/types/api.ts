/**
 * TypeScript contract for the Medical Handover Quality Agent API.
 *
 * These interfaces mirror the Django serializers exactly — do not guess shapes
 * that differ from `backend/handovers/serializers.py`.
 */

export type Mode = "baseline" | "advanced";

export type AnalysisStatus = "pending" | "running" | "completed" | "failed";

export type ReviewDecision = "accepted" | "rejected" | "edited";

export type FindingStatus = "omitted" | "partially_omitted";

export type Importance = "critical" | "high" | "medium" | "low";

export interface ReviewSummary {
  total: number;
  accepted: number;
  rejected: number;
  edited: number;
  pending: number;
}

export interface PatientProfile {
  case_id?: string;
  title?: string;
  difficulty?: string;
  patient_id?: string;
  age?: number;
  sex?: string;
  admission_reason?: string;
  current_location?: string;
  [key: string]: unknown;
}

export interface RecordItem {
  filename: string;
  content: string;
}

export interface AnalysisListItem {
  id: number;
  created_at: string;
  updated_at: string;
  mode: Mode;
  status: AnalysisStatus;
  finding_count: number;
  review_summary: ReviewSummary;
}

export interface FindingReview {
  decision: ReviewDecision;
  comment: string;
  edited_summary: string;
  edited_category: string;
  edited_importance: string;
  edited_status: string;
  reviewed_at: string;
}

export interface FindingEvidence {
  filename: string;
  content: string;
}

export type FindingOriginal = {
  category: string;
  importance: string;
  status: string;
  summary: string;
  evidence_sources: string[];
};

export interface Finding {
  id: number;
  order: number;
  category: string;
  importance: string;
  status: string;
  summary: string;
  evidence_sources: string[];
  /** The raw AI finding dict, preserved verbatim. */
  original: FindingOriginal;
  /** Evidence resolved back to the submitted record content. */
  evidence: FindingEvidence[];
  /** Human review decision, if any. */
  review: FindingReview | null;
}

export interface EngineMeta {
  backend?: string;
  stages?: string[];
  timing_s?: Record<string, number | null>;
  tokens?: Record<string, unknown>;
  logs?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface AnalysisDetail {
  id: number;
  created_at: string;
  updated_at: string;
  mode: Mode;
  status: AnalysisStatus;
  patient_profile: PatientProfile;
  records: RecordItem[];
  handover: string;
  engine_meta: EngineMeta;
  error: string;
  findings: Finding[];
  review_summary: ReviewSummary;
}

export interface AnalysisInput {
  patient_profile: PatientProfile;
  records: RecordItem[];
  handover: string;
  mode: Mode;
}

export interface ReviewPayload {
  decision: ReviewDecision;
  comment?: string;
  edited_summary?: string;
  edited_category?: string;
  edited_status?: string;
  edited_importance?: string;
}

export interface ReviewResponse {
  decision: ReviewDecision;
  comment: string;
  edited_summary: string;
  edited_category: string;
  edited_importance: string;
  edited_status: string;
  reviewed_at: string;
  finding_id: number;
  analysis_id: number;
}

export interface HealthResponse {
  status: string;
  service: string;
}

export interface AnalysisListResponse {
  count: number;
  results: AnalysisListItem[];
}

/** Error payload shape returned for 400 responses. */
export interface ApiErrorPayload {
  detail?: string;
  errors?: Record<string, unknown>;
}