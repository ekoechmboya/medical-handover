"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Check,
  CircleAlert,
  FileSearch,
  PencilLine,
  Sparkles,
  UserRound,
} from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  CategoryBadge,
  ImportanceBadge,
  FindingStatusBadge,
} from "@/components/findings/FindingChips";
import { EvidenceList } from "@/components/findings/EvidenceList";
import { ReviewEditorModal } from "@/components/findings/ReviewEditorModal";
import { DECISION_DEFS } from "@/lib/constants";
import { formatTime } from "@/lib/format";
import { cn } from "@/lib/cn";
import { api } from "@/lib/api";

import type { Finding, FindingReview, ReviewDecision, ReviewPayload } from "@/types/api";

export interface ReviewChangeResult {
  findingId: number;
  review: FindingReview;
  summaryDelta: { before: ReviewDecision | "pending"; after: ReviewDecision };
}

interface FindingCardProps {
  finding: Finding;
  analysisId: number | string;
  onReviewChange: (result: ReviewChangeResult) => void;
}

function toReview(input: {
  decision: ReviewDecision;
  comment: string;
  edited_summary: string;
  edited_category: string;
  edited_importance: string;
  edited_status: string;
  reviewed_at: string;
}): FindingReview {
  return {
    decision: input.decision,
    comment: input.comment,
    edited_summary: input.edited_summary,
    edited_category: input.edited_category,
    edited_importance: input.edited_importance,
    edited_status: input.edited_status,
    reviewed_at: input.reviewed_at,
  };
}

export function FindingCard({ finding, analysisId, onReviewChange }: FindingCardProps) {
  const [submitting, setSubmitting] = useState<"accepted" | "rejected" | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const review = finding.review;
  const currentDecision: ReviewDecision | "pending" = review?.decision ?? "pending";
  const decisionDef = DECISION_DEFS[currentDecision];
  const DecisionIcon = decisionDef.icon;

  const submitDecision = async (decision: "accepted" | "rejected") => {
    setSubmitting(decision);
    setError(null);
    try {
      const response = await api.submitReview(analysisId, finding.id, { decision });
      onReviewChange({
        findingId: finding.id,
        review: toReview(response),
        summaryDelta: { before: currentDecision, after: decision },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your decision.");
    } finally {
      setSubmitting(null);
    }
  };

  const submitEdited = async (payload: ReviewPayload) => {
    const response = await api.submitReview(analysisId, finding.id, payload);
    onReviewChange({
      findingId: finding.id,
      review: toReview(response),
      summaryDelta: { before: currentDecision, after: "edited" },
    });
  };

  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="rounded-xl border border-line bg-surface shadow-[0_1px_2px_rgba(16,24,40,0.04)]"
    >
      <div className="p-5">
        {/* Header: identity chips. */}
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="inline-flex h-6 min-w-6 items-center justify-center rounded-md border border-line bg-background px-1.5 font-mono text-xs font-semibold text-muted"
            aria-label={`Finding number ${finding.order + 1}`}
          >
            {finding.order + 1}
          </span>
          <CategoryBadge category={finding.category} />
          <span className="mx-0.5 hidden h-4 w-px bg-line sm:block" aria-hidden="true" />
          <ImportanceBadge importance={finding.importance} />
          <FindingStatusBadge status={finding.status} />
          {review ? (
            <Badge
              tone={decisionDef.tone}
              icon={<DecisionIcon aria-hidden="true" />}
              className="ml-auto"
            >
              {decisionDef.label}
            </Badge>
          ) : null}
        </div>

        {/* AI finding — always the original output. */}
        <div className="mt-4">
          <div className="flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-brand-600" aria-hidden="true" />
            <span className="text-[11px] font-semibold uppercase tracking-wider text-brand-800">
              AI finding
            </span>
          </div>
          <p className="mt-1.5 text-[15px] leading-relaxed text-ink">
            {finding.summary}
          </p>
        </div>

        {/* Human review — stored separately, never mutates the AI output. */}
        {review ? (
          <div className="mt-4 rounded-lg border border-line bg-background/50 p-3.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <UserRound className="h-3.5 w-3.5 text-violet-600" aria-hidden="true" />
                <span className="text-[11px] font-semibold uppercase tracking-wider text-violet-800">
                  Human review
                </span>
              </div>
              {review.reviewed_at ? (
                <span className="text-[11px] text-muted">
                  Decided {formatTime(review.reviewed_at)}
                </span>
              ) : null}
            </div>

            {review.decision === "edited" && review.edited_summary ? (
              <div className="mt-2.5 rounded-md border border-violet-200 bg-violet-50/70 p-3">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-violet-600">
                  Reviewer revision
                </span>
                <p className="mt-1 text-sm leading-relaxed text-ink-soft">
                  {review.edited_summary}
                </p>
                <div className="mt-2.5 flex flex-wrap gap-1.5">
                  {review.edited_category ? (
                    <CategoryBadge category={review.edited_category} />
                  ) : null}
                  {review.edited_importance ? (
                    <ImportanceBadge importance={review.edited_importance} />
                  ) : null}
                  {review.edited_status ? (
                    <FindingStatusBadge status={review.edited_status} />
                  ) : null}
                </div>
              </div>
            ) : null}

            {review.comment ? (
              <p className="mt-2.5 text-xs leading-relaxed text-muted">
                <span className="font-semibold text-ink-soft">Comment: </span>
                {review.comment}
              </p>
            ) : null}
          </div>
        ) : (
          <p className="mt-3 text-xs text-muted">
            Awaiting a human decision for this candidate finding.
          </p>
        )}
      </div>

      {/* Supporting evidence. */}
      {finding.evidence.length > 0 || finding.evidence_sources.length > 0 ? (
        <div className="border-t border-line bg-background/40 px-5 py-4">
          <div className="mb-2.5 flex items-center gap-1.5">
            <FileSearch className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-600">
              Supporting evidence
            </span>
            <span className="text-[11px] text-faint">
              · {finding.evidence_sources.length} source
              {finding.evidence_sources.length === 1 ? "" : "s"}
            </span>
          </div>
          <EvidenceList evidence={finding.evidence} sourceNames={finding.evidence_sources} />
        </div>
      ) : null}

      {/* Human review actions. */}
      <div className="flex flex-wrap items-center gap-2 border-t border-line px-5 py-3.5">
        <Button
          size="sm"
          variant={currentDecision === "accepted" ? "success" : "secondary"}
          onClick={() => void submitDecision("accepted")}
          loading={submitting === "accepted"}
          aria-label={`Accept finding ${finding.order + 1}`}
        >
          <Check className="h-3.5 w-3.5" aria-hidden="true" />
          Accept
        </Button>
        <Button
          size="sm"
          variant={currentDecision === "rejected" ? "danger" : "secondary"}
          onClick={() => void submitDecision("rejected")}
          loading={submitting === "rejected"}
          aria-label={`Reject finding ${finding.order + 1}`}
        >
          <CircleAlert className="h-3.5 w-3.5" aria-hidden="true" />
          Reject
        </Button>
        <Button
          size="sm"
          variant={currentDecision === "edited" ? "primary" : "secondary"}
          onClick={() => setEditorOpen(true)}
          aria-label={`Edit finding ${finding.order + 1}`}
        >
          <PencilLine className="h-3.5 w-3.5" aria-hidden="true" />
          Edit
        </Button>
        <span className={cn("ml-auto text-[11px] text-muted")}>
          {currentDecision === "pending"
            ? "No decision recorded"
            : `Marked ${decisionDef.label.toLowerCase()}`}
        </span>
      </div>

      {error ? (
        <p
          role="alert"
          className="border-t border-rose-100 bg-rose-50/60 px-5 py-2.5 text-xs font-medium text-rose-800"
        >
          {error}
        </p>
      ) : null}

      <ReviewEditorModal
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        finding={finding}
        onSubmit={submitEdited}
      />
    </motion.article>
  );
}