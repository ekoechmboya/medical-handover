"use client";

import { useState } from "react";
import { Scale } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { CategoryBadge, ImportanceBadge, FindingStatusBadge } from "@/components/findings/FindingChips";
import {
  categoryDef,
  IMPORTANCE_DEFS,
  IMPORTANCE_LEVELS,
  STATUS_DEFS,
  FINDING_STATUSES,
} from "@/lib/constants";

import type { Finding, ReviewPayload } from "@/types/api";

export interface EditedValues {
  summary: string;
  category: string;
  importance: string;
  status: string;
  comment: string;
}

interface ReviewEditorModalProps {
  open: boolean;
  onClose: () => void;
  finding: Finding;
  onSubmit: (payload: ReviewPayload) => Promise<void>;
}

const CATEGORY_OPTIONS = [
  "allergy_or_adverse_reaction",
  "clinical_status",
  "escalation",
  "medication",
  "monitoring",
  "pending_consult",
  "pending_investigation",
  "pending_result",
  "procedure",
  "safety",
];

const IMPORTANCE_OPTION_LABELS = IMPORTANCE_LEVELS.map((level) => ({
  value: level,
  label: IMPORTANCE_DEFS[level].label,
}));

const STATUS_OPTION_LABELS = FINDING_STATUSES.map((status) => ({
  value: status,
  label: STATUS_DEFS[status].label,
}));

const CATEGORY_OPTION_LABELS = CATEGORY_OPTIONS.map((c) => ({
  value: c,
  label: categoryDef(c).label,
}));

export function ReviewEditorModal({ open, onClose, finding, onSubmit }: ReviewEditorModalProps) {
  const defaultValues: EditedValues = {
    summary:
      finding.review?.decision === "edited" && finding.review.edited_summary
        ? finding.review.edited_summary
        : finding.summary,
    category:
      finding.review?.decision === "edited" && finding.review.edited_category
        ? finding.review.edited_category
        : finding.category,
    importance:
      finding.review?.decision === "edited" && finding.review.edited_importance
        ? finding.review.edited_importance
        : finding.importance,
    status:
      finding.review?.decision === "edited" && finding.review.edited_status
        ? finding.review.edited_status
        : finding.status,
    comment: finding.review?.comment ?? "",
  };

  const [values, setValues] = useState<EditedValues>(defaultValues);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setValues(defaultValues);
    setError(null);
    setSaving(false);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleSave = async () => {
    if (!values.summary.trim()) {
      setError("A revised summary is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        decision: "edited",
        comment: values.comment,
        edited_summary: values.summary.trim(),
        edited_category: values.category,
        edited_importance: values.importance,
        edited_status: values.status,
      });
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the revision.");
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Edit finding"
      description="Revise the wording a reviewer will carry forward. The original AI finding stays untouched."
      labelledBy="review-editor-title"
      footer={
        <>
          <Button variant="secondary" onClick={handleClose} disabled={saving}>
            Cancel
          </Button>
          <Button variant="primary" onClick={() => void handleSave()} loading={saving}>
            Save revision
          </Button>
        </>
      }
    >
      <div className="space-y-5">
        {/* Original AI finding — always visible, read-only. */}
        <div className="relative rounded-xl border border-brand-200 bg-brand-50/70 p-4">
          <div className="mb-2 flex items-center gap-2 border-b border-brand-100 pb-2">
            <Scale className="h-3.5 w-3.5 text-brand-700" aria-hidden="true" />
            <span className="text-xs font-semibold uppercase tracking-wide text-brand-800">
              Original AI finding
            </span>
          </div>
          <p className="text-sm leading-relaxed text-ink-soft">{finding.summary}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            <CategoryBadge category={finding.category} />
            <ImportanceBadge importance={finding.importance} />
            <FindingStatusBadge status={finding.status} />
          </div>
        </div>

        {/* Reviewer revision form. */}
        <div>
          <label htmlFor="edit-summary" className="mb-1.5 block text-sm font-medium text-ink-soft">
            Reviewer revision <span className="text-rose-500">*</span>
          </label>
          <div className="relative">
            <span className="pointer-events-none absolute left-3 top-2.5 text-[11px] font-semibold uppercase tracking-wide text-violet-500">
              Reviewer
            </span>
            <textarea
              id="edit-summary"
              value={values.summary}
              onChange={(e) => setValues((v) => ({ ...v, summary: e.target.value }))}
              rows={3}
              className="w-full resize-y rounded-lg border border-line bg-white px-3 pb-2 pt-8 text-sm leading-relaxed text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
              placeholder="Revised wording of the finding…"
            />
          </div>
          {error ? (
            <p className="mt-1.5 text-xs font-medium text-rose-700" role="alert">
              {error}
            </p>
          ) : null}
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label htmlFor="edit-category" className="mb-1.5 block text-sm font-medium text-ink-soft">
              Category
            </label>
            <select
              id="edit-category"
              value={values.category}
              onChange={(e) => setValues((v) => ({ ...v, category: e.target.value }))}
              className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
            >
              {CATEGORY_OPTION_LABELS.map(({ value, label }) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="edit-importance" className="mb-1.5 block text-sm font-medium text-ink-soft">
              Importance
            </label>
            <select
              id="edit-importance"
              value={values.importance}
              onChange={(e) => setValues((v) => ({ ...v, importance: e.target.value }))}
              className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
            >
              {IMPORTANCE_OPTION_LABELS.map(({ value, label }) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="edit-status" className="mb-1.5 block text-sm font-medium text-ink-soft">
              Status
            </label>
            <select
              id="edit-status"
              value={values.status}
              onChange={(e) => setValues((v) => ({ ...v, status: e.target.value }))}
              className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
            >
              {STATUS_OPTION_LABELS.map(({ value, label }) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="edit-comment" className="mb-1.5 block text-sm font-medium text-ink-soft">
            Reviewer comment
          </label>
          <textarea
            id="edit-comment"
            value={values.comment}
            onChange={(e) => setValues((v) => ({ ...v, comment: e.target.value }))}
            rows={2}
            className="w-full resize-y rounded-lg border border-line bg-white px-3 py-2 text-sm leading-relaxed text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
            placeholder="Optional note for the next reviewer…"
          />
        </div>

        <p className="text-xs leading-relaxed text-muted">
          The backend stores human edits separately from the AI output. Re-reviewing
          a finding only updates this decision — it never overwrites the original
          finding.
        </p>
      </div>
    </Modal>
  );
}