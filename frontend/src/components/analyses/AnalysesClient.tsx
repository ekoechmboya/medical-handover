"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowRight, ClipboardList, FolderOpen, Plus, RefreshCw } from "lucide-react";
import Link from "next/link";

import { ModeBadge } from "@/components/analysis/ModeBadge";
import { AnalysisStatusBadge } from "@/components/analysis/AnalysisStatusBadge";
import { ReviewSummaryCompact } from "@/components/analysis/ReviewSummaryCompact";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineError } from "@/components/ui/InlineError";
import { Spinner } from "@/components/ui/Spinner";
import { api } from "@/lib/api";
import { formatDateTime, timeAgo } from "@/lib/format";

import type { AnalysisListItem } from "@/types/api";

export function AnalysesClient() {
  const [items, setItems] = useState<AnalysisListItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listAnalyses();
      setItems(response.results);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Analysis history</h1>
          <p className="mt-1 text-sm text-muted">
            Every run — baseline or advanced — with its findings and human review progress.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => void load()} loading={loading}>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Refresh
          </Button>
          <Button href="/workspace">
            <Plus className="h-4 w-4" aria-hidden="true" />
            New analysis
          </Button>
        </div>
      </div>

      {loading && !items ? (
        <div className="flex justify-center py-24">
          <Spinner label="Loading analyses…" />
        </div>
      ) : null}

      {error ? (
        <InlineError
          title="Could not load analyses"
          error={error}
          onRetry={() => void load()}
        />
      ) : null}

      {!loading && !error && items && items.length === 0 ? (
        <EmptyState
          icon={<ClipboardList aria-hidden="true" />}
          title="No analyses yet"
          description="Run your first analysis from the workspace — load the demo scenario and the workflow will take you through the whole review loop."
          action={
            <Button href="/workspace">
              Open Analysis Workspace
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          }
        />
      ) : null}

      {items && items.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((item) => {
            const reviewed =
              item.review_summary.accepted +
              item.review_summary.rejected +
              item.review_summary.edited;
            const canHandoff =
              item.status === "completed" &&
              item.review_summary.total > 0 &&
              reviewed === item.review_summary.total;
            return (
              <div
                key={item.id}
                className="group flex flex-col rounded-xl border border-line bg-surface transition hover:border-line-strong hover:shadow-[0_4px_16px_rgba(16,24,40,0.07)]"
              >
                <Link
                  href={`/analyses/${item.id}`}
                  className="flex-1 p-5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-semibold text-ink">
                        #{item.id}
                      </span>
                      <ModeBadge mode={item.mode} size="sm" />
                    </div>
                    <AnalysisStatusBadge status={item.status} />
                  </div>

                  <div className="mt-3 flex items-center gap-3 text-xs text-muted">
                    <span title={formatDateTime(item.created_at)}>
                      {timeAgo(item.created_at)}
                    </span>
                    <span aria-hidden="true">·</span>
                    <span>
                      {item.finding_count} finding{item.finding_count === 1 ? "" : "s"}
                    </span>
                    <span aria-hidden="true">·</span>
                    <span>
                      {reviewed}/{item.review_summary.total} reviewed
                    </span>
                  </div>

                  <div className="mt-4">
                    <ReviewSummaryCompact summary={item.review_summary} />
                  </div>
                </Link>

                <div className="flex items-center justify-between gap-3 border-t border-line px-5 py-3">
                  <span className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 transition group-hover:gap-1.5">
                    Open review
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </span>
                  {canHandoff ? (
                    <Button size="sm" variant="secondary" href={`/analyses/${item.id}/handover`}>
                      Final handover
                    </Button>
                  ) : (
                    <span className="text-[11px] text-faint">
                      Final handover after review
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}

      {!loading && !error && items && items.length > 0 ? (
        <p className="mt-6 flex items-center justify-center gap-1.5 text-center text-xs text-faint">
          <FolderOpen className="h-3.5 w-3.5" aria-hidden="true" />
          Open a review to decide findings — a fully reviewed analysis unlocks the
          final handover for the receiving clinician.
        </p>
      ) : null}
    </div>
  );
}