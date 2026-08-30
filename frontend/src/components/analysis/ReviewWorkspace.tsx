"use client";

import { useEffect, useState } from "react";
import { ClipboardList, CircleAlert } from "lucide-react";

import { PatientPanel } from "@/components/analysis/PatientPanel";
import { ReviewSummaryPanel } from "@/components/analysis/ReviewSummaryPanel";
import { ReviewSummaryCompact } from "@/components/analysis/ReviewSummaryCompact";
import { FindingCard, type ReviewChangeResult } from "@/components/findings/FindingCard";
import { ReviewGuide } from "@/components/review/ReviewGuide";
import { HowSystemWorks } from "@/components/review/HowSystemWorks";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";

import type { AnalysisDetail, Finding, ReviewSummary } from "@/types/api";

interface ReviewWorkspaceProps {
  analysis: AnalysisDetail;
  onAnalysisChange?: (analysis: AnalysisDetail) => void;
}

export function ReviewWorkspace({ analysis, onAnalysisChange }: ReviewWorkspaceProps) {
  const [findings, setFindings] = useState<Finding[]>(analysis.findings);
  const [summary, setSummary] = useState<ReviewSummary>(analysis.review_summary);

  useEffect(() => {
    setFindings(analysis.findings);
    setSummary(analysis.review_summary);
  }, [analysis.id, analysis.findings, analysis.review_summary]);

  const handleReviewChange = (result: ReviewChangeResult) => {
    const nextFindings = findings.map((finding) =>
      finding.id === result.findingId ? { ...finding, review: result.review } : finding,
    );
    const nextSummary = applyReviewDelta(summary, result.summaryDelta);
    setFindings(nextFindings);
    setSummary(nextSummary);
    onAnalysisChange?.({
      ...analysis,
      findings: nextFindings,
      review_summary: nextSummary,
    });
  };

  if (analysis.status === "failed") {
    return (
      <div className="mx-auto max-w-2xl space-y-4 py-8">
        <EmptyState
          icon={<CircleAlert aria-hidden="true" />}
          title="Analysis failed"
          description={
            analysis.error ||
            "The analysis engine reported an error. This can happen when a live model backend is unavailable or a quota is exceeded."
          }
          action={
            <Button variant="secondary" href="/workspace">
              Start a new analysis
            </Button>
          }
        />
      </div>
    );
  }

  if (findings.length === 0) {
    return (
      <div className="mx-auto max-w-2xl space-y-4 py-8">
        <EmptyState
          icon={<ClipboardList aria-hidden="true" />}
          title="No candidate findings"
          description="The engine found no clinically important omissions between the records and the handover. Nothing for a reviewer to decide on."
          action={
            analysis.mode === "baseline" ? (
              <Button variant="secondary" href="/workspace">
                Try the Advanced Agent
              </Button>
            ) : undefined
          }
        />
      </div>
    );
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)_300px]">
      {/* Patient context + sources */}
      <aside>
        <PatientPanel analysis={analysis} />
      </aside>

      {/* Findings + human decisions */}
      <section aria-label="AI findings">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold tracking-tight">
            Candidate findings{" "}
            <span className="font-normal text-muted">({findings.length})</span>
          </h2>
          <ReviewSummaryCompact summary={summary} />
        </div>
        <ul className="space-y-4">
          {findings.map((finding) => (
            <li key={finding.id}>
              <FindingCard
                finding={finding}
                analysisId={analysis.id}
                onReviewChange={handleReviewChange}
              />
            </li>
          ))}
        </ul>
      </section>

      {/* Human review + summary */}
      <aside className="space-y-4 xl:sticky xl:top-20 xl:self-start">
        <ReviewSummaryPanel summary={summary} />
        <ReviewGuide />
        <HowSystemWorks compact />
      </aside>
    </div>
  );
}

function applyReviewDelta(
  summary: ReviewSummary,
  delta: { before: "pending" | "accepted" | "rejected" | "edited"; after: "accepted" | "rejected" | "edited" },
): ReviewSummary {
  if (delta.before === delta.after) return summary;
  const next: ReviewSummary = { ...summary };
  if (delta.before === "pending") {
    next.pending = Math.max(0, next.pending - 1);
  } else {
    next[delta.before] = Math.max(0, next[delta.before] - 1);
  }
  next[delta.after] += 1;
  return next;
}