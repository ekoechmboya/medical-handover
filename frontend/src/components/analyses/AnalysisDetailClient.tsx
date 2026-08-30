"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, ChevronRight, ClipboardList, FileCheck2 } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ModeBadge } from "@/components/analysis/ModeBadge";
import { AnalysisStatusBadge } from "@/components/analysis/AnalysisStatusBadge";
import { ReviewSummaryPanel } from "@/components/analysis/ReviewSummaryPanel";
import { ReviewWorkspace } from "@/components/analysis/ReviewWorkspace";
import { AgentPipeline } from "@/components/pipeline/AgentPipeline";
import { InlineError } from "@/components/ui/InlineError";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { Spinner } from "@/components/ui/Spinner";
import { FinalHandoverView } from "@/components/handover/FinalHandoverView";
import { api } from "@/lib/api";
import { formatDateTime, formatStageSeconds, timeAgo } from "@/lib/format";
import { ENGINE_BACKEND_LABEL } from "@/lib/constants";

import type { AnalysisDetail, ReviewSummary } from "@/types/api";

const VIEW_TABS = [
  {
    value: "review",
    label: "Review workspace",
    description: "Decide each finding",
    icon: <ClipboardList aria-hidden="true" />,
  },
  {
    value: "final",
    label: "Final handover",
    description: "Assembled for the receiving clinician",
    icon: <FileCheck2 aria-hidden="true" />,
  },
];

export function AnalysisDetailClient() {
  const params = useParams<{ id: string }>();
  const analysisId = params?.id ?? "";

  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [reviewSummary, setReviewSummary] = useState<ReviewSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [view, setView] = useState<"review" | "final">("review");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const detail = await api.getAnalysis(analysisId);
      setAnalysis(detail);
      try {
        const summary = await api.getReviewSummary(analysisId);
        setReviewSummary(summary);
      } catch {
        setReviewSummary(null);
      }
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [analysisId]);

  useEffect(() => {
    if (analysisId) void load();
  }, [analysisId, load]);

  if (loading && !analysis) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
        <Spinner label="Loading analysis…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 sm:px-6 lg:px-8">
        <InlineError
          title="Could not load this analysis"
          error={error}
          onRetry={() => void load()}
        />
        <div className="mt-4">
          <Link
            href="/analyses"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-muted transition hover:text-ink"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to analysis history
          </Link>
        </div>
      </div>
    );
  }

  if (!analysis) return null;

  const meta = analysis.engine_meta ?? {};
  const stages = Array.isArray(meta.stages) ? meta.stages : [];
  const backendLabel = ENGINE_BACKEND_LABEL[String(meta.backend ?? "")] ?? null;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <nav className="mb-4 flex items-center gap-1.5 text-sm" aria-label="Breadcrumb">
        <Link
          href="/analyses"
          className="font-medium text-muted transition hover:text-ink"
        >
          Analyses
        </Link>
        <ChevronRight className="h-3.5 w-3.5 text-faint" aria-hidden="true" />
        <span className="font-medium text-ink">Analysis #{analysis.id}</span>
      </nav>
      <header className="mb-6 rounded-xl border border-line bg-surface p-5">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-xl font-semibold tracking-tight">
                  Analysis #{analysis.id}
                </h1>
                <ModeBadge mode={analysis.mode} />
                <AnalysisStatusBadge status={analysis.status} />
              </div>
              <div className="flex items-center gap-2 text-xs text-muted">
                <span title={formatDateTime(analysis.created_at)}>
                  Created {timeAgo(analysis.created_at)}
                </span>
                <span aria-hidden="true">·</span>
                <span title={formatDateTime(analysis.updated_at)}>
                  Updated {timeAgo(analysis.updated_at)}
                </span>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-line pt-4 text-xs text-muted">
              {backendLabel ? (
                <span>
                  <span className="font-semibold text-ink-soft">Engine: </span>
                  {backendLabel}
                </span>
              ) : null}
              <span>
                <span className="font-semibold text-ink-soft">Findings: </span>
                {analysis.findings.length}
              </span>
              {analysis.mode === "advanced" && stages.length > 1 ? (
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-ink-soft">Pipeline:</span>
                  <AgentPipeline stages={stages} compact />
                </span>
              ) : null}
              {Object.keys(meta.timing_s ?? {}).length > 0 ? (
                <span>
                  <span className="font-semibold text-ink-soft">Stage timing: </span>
                  {Object.entries(meta.timing_s as Record<string, number | null>)
                    .map(([stage, seconds]) => {
                      const rendered = formatStageSeconds(seconds);
                      return rendered ? `${stage} ${rendered}` : null;
                    })
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              ) : null}
            </div>
          </div>

          <ReviewSummaryPanel
            summary={reviewSummary ?? analysis.review_summary}
            className="w-full shrink-0 border-0 bg-transparent p-0 lg:w-80"
          />
        </div>
      </header>

      <SegmentedControl
        options={VIEW_TABS}
        value={view}
        onChange={(value) => setView(value as "review" | "final")}
        name="analysis-views"
        className="mb-6"
      />

      {view === "review" ? (
        <div id="review-workspace">
          <ReviewWorkspace
            analysis={{
              ...analysis,
              review_summary: reviewSummary ?? analysis.review_summary,
            }}
            onAnalysisChange={setAnalysis}
          />
        </div>
      ) : (
        <FinalHandoverView
          analysis={{
            ...analysis,
            review_summary: reviewSummary ?? analysis.review_summary,
          }}
          summary={reviewSummary ?? analysis.review_summary}
        />
      )}
    </div>
  );
}