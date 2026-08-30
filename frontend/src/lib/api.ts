/**
 * Typed API client for the Medical Handover Quality Agent backend.
 *
 * Base URL comes from NEXT_PUBLIC_API_BASE_URL; the default is the deployed
 * Render backend. Override with an env var when pointing at a local Django
 * instance (e.g. NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000).
 */

import type {
  AnalysisDetail,
  AnalysisInput,
  AnalysisListResponse,
  HealthResponse,
  ReviewPayload,
  ReviewResponse,
  ReviewSummary,
} from "@/types/api";

export const DEFAULT_API_BASE_URL = "https://medical-handover.onrender.com";

export function apiBaseUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  return url && url.length > 0 ? url.replace(/\/+$/, "") : DEFAULT_API_BASE_URL;
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly errors: Record<string, unknown> | null;

  constructor(message: string, status: number, errors: Record<string, unknown> | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = message;
    this.errors = errors;
  }
}

async function request<T>(path: string, init?: RequestInit, timeoutMs?: number): Promise<T> {
  const controller = new AbortController();
  const timer =
    timeoutMs != null
      ? setTimeout(() => controller.abort(), timeoutMs)
      : undefined;

  const headers = new Headers(init?.headers);
  if (init?.body) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      headers,
      signal: controller.signal,
    });
  } catch {
    if (controller.signal.aborted) {
      throw new ApiError("The request timed out. Check that the backend is reachable.", 0, null);
    }
    throw new ApiError(
      "Could not reach the analysis backend. Is the Django server running at " +
        `${apiBaseUrl()}?`,
      0,
      null,
    );
  } finally {
    if (timer != null) clearTimeout(timer);
  }

  if (!response.ok) {
    let detail = `Request failed with HTTP ${response.status}.`;
    let errors: Record<string, unknown> | null = null;
    try {
      const body = (await response.json()) as { detail?: string; errors?: Record<string, unknown> };
      if (body?.detail) detail = body.detail;
      if (body?.errors) errors = body.errors;
    } catch {
      // Non-JSON error body; keep the default message.
    }
    throw new ApiError(detail, response.status, errors);
  }

  return (await response.json()) as T;
}

/**
 * POST /api/analyses/ is async by design: the row is created and the engine runs
 * in the background, so the request itself resolves quickly even on the live
 * Gemini backend. The generous window below only guards a slow/unwarm pod.
 */
const CREATE_TIMEOUT_MS = 60 * 1000;

/** Interval between status polls while awaiting a terminal status. */
const POLL_INTERVAL_MS = 2000;

/** Terminal statuses that end a poll loop. */
function isTerminal(status: string): boolean {
  return status === "completed" || status === "failed";
}

export const api = {
  async health(): Promise<HealthResponse> {
    return request<HealthResponse>("/api/health/");
  },

  async listAnalyses(): Promise<AnalysisListResponse> {
    return request<AnalysisListResponse>("/api/analyses/");
  },

  async getAnalysis(id: number | string): Promise<AnalysisDetail> {
    return request<AnalysisDetail>(`/api/analyses/${id}/`);
  },

  async createAnalysis(input: AnalysisInput): Promise<AnalysisDetail> {
    return request<AnalysisDetail>(
      "/api/analyses/",
      { method: "POST", body: JSON.stringify(input) },
      CREATE_TIMEOUT_MS,
    );
  },

  /**
   * Poll an analysis until it reaches a terminal status. Never aborts: a live
   * Gemini run may take several minutes, so the caller waits for as long as the
   * backend needs.
   */
  async waitForAnalysis(
    id: number | string,
    onUpdate?: (detail: AnalysisDetail) => void,
  ): Promise<AnalysisDetail> {
    for (;;) {
      const detail = await this.getAnalysis(id);
      onUpdate?.(detail);
      if (isTerminal(detail.status)) return detail;
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    }
  },

  async submitReview(
    analysisId: number | string,
    findingId: number,
    payload: ReviewPayload,
  ): Promise<ReviewResponse> {
    return request<ReviewResponse>(
      `/api/analyses/${analysisId}/findings/${findingId}/review/`,
      { method: "POST", body: JSON.stringify(payload) },
    );
  },

  async getReviewSummary(analysisId: number | string): Promise<ReviewSummary> {
    return request<ReviewSummary>(`/api/analyses/${analysisId}/review-summary/`);
  },
};