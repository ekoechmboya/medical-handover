"use client";

import { useState } from "react";
import { ArrowRight, Check, ClipboardCheck, Copy, FileDown } from "lucide-react";

import { HandoverDocument } from "@/components/handover/HandoverDocument";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  buildFinalHandover,
  finalHandoverText,
} from "@/lib/finalHandover";

import type { AnalysisDetail, ReviewSummary } from "@/types/api";

interface FinalHandoverViewProps {
  analysis: AnalysisDetail;
  summary: ReviewSummary;
}

export function FinalHandoverView({ analysis, summary }: FinalHandoverViewProps) {
  const data = buildFinalHandover(analysis);
  const [copied, setCopied] = useState(false);

  const allDecided = summary.pending === 0 && summary.total > 0;

  if (!allDecided) {
    return (
      <div className="space-y-4">
        <header className="flex items-center gap-2">
          <ClipboardCheck className="h-5 w-5 text-brand-700" aria-hidden="true" />
          <h2 className="text-lg font-semibold tracking-tight">Final handover</h2>
        </header>
        <EmptyState
          icon={<FileDown aria-hidden="true" />}
          title="Finish the review to assemble the final handover"
          description="The final handover combines the current handover with every finding you accept or edit. Findings still pending review are excluded until you decide on them."
          action={
            <Button
              variant="secondary"
              onClick={() =>
                document
                  .getElementById("review-workspace")
                  ?.scrollIntoView({ behavior: "smooth", block: "start" })
              }
            >
              Back to review workspace
            </Button>
          }
        />
      </div>
    );
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(finalHandoverText(data));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-line bg-surface p-5">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Final handover</h2>
          <p className="mt-1 text-sm leading-relaxed text-muted">
            From {data.decided} decided findings, {data.included} item
            {data.included === 1 ? "" : "s"} are included in the handover
            {data.rejected > 0 ? ` and ${data.rejected} rejected` : ""} ·{" "}
            {data.pending} pending.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="secondary" onClick={handleCopy}>
            {copied ? (
              <Check className="h-4 w-4 text-emerald-600" aria-hidden="true" />
            ) : (
              <Copy className="h-4 w-4" aria-hidden="true" />
            )}
            {copied ? "Copied to clipboard" : "Copy handover text"}
          </Button>
          <Button href={`/analyses/${analysis.id}/handover`}>
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
            Open for receiving clinician
          </Button>
        </div>
      </header>

      <HandoverDocument data={data} />

      <p className="flex items-center gap-1.5 text-xs leading-relaxed text-muted">
        <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
        Rejected findings are excluded from the document and recorded in the review
        history above.
      </p>
    </div>
  );
}