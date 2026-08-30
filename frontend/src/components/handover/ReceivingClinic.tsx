"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Printer } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { HandoverDocument } from "@/components/handover/HandoverDocument";
import { Button } from "@/components/ui/Button";
import { InlineError } from "@/components/ui/InlineError";
import { Spinner } from "@/components/ui/Spinner";
import { api } from "@/lib/api";
import { buildFinalHandover } from "@/lib/finalHandover";

import type { AnalysisDetail } from "@/types/api";

export function ReceivingClinic() {
  const params = useParams<{ id: string }>();
  const analysisId = params?.id ?? "";

  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const detail = await api.getAnalysis(analysisId);
      setAnalysis(detail);
    } catch (err) {
      setError(err);
    }
  }, [analysisId]);

  useEffect(() => {
    if (analysisId) void load();
  }, [analysisId, load]);

  if (!analysis && !error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6 lg:px-8">
        <Spinner label="Loading final handover…" />
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 sm:px-6 lg:px-8">
        <InlineError
          title="Could not load the final handover"
          error={error}
          onRetry={() => void load()}
        />
      </div>
    );
  }

  const data = buildFinalHandover(analysis);

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8 print:max-w-none print:px-0 print:py-0">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-4 print:hidden">
        <Link
          href={`/analyses/${analysis.id}`}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-muted transition hover:text-ink"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to analysis review
        </Link>
        <Button onClick={() => window.print()}>
          <Printer className="h-4 w-4" aria-hidden="true" />
          Print / Save as PDF
        </Button>
      </div>

      <HandoverDocument data={data} standalone />
    </div>
  );
}