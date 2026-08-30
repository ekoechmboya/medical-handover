import type { AnalysisDetail, Finding, ReviewDecision } from "@/types/api";
import { categoryDef } from "@/lib/constants";

export interface FinalHandoverItem {
  findingId: number;
  decision: ReviewDecision;
  category: string;
  categoryLabel: string;
  importance: string;
  status: string;
  summary: string;
  comment?: string;
}

export interface FinalHandoverData {
  analysis: AnalysisDetail;
  items: FinalHandoverItem[];
  decided: number;
  included: number;
  rejected: number;
  pending: number;
}

const DECISION_LABELS: Record<ReviewDecision, string> = {
  accepted: "Accepted",
  rejected: "Rejected",
  edited: "Edited",
};

const decisionOf = (finding: Finding): ReviewDecision | null =>
  finding.review?.decision ?? null;

export function buildFinalHandover(analysis: AnalysisDetail): FinalHandoverData {
  const items: FinalHandoverItem[] = [];
  let rejected = 0;
  let pending = 0;

  for (const finding of analysis.findings) {
    const decision = decisionOf(finding);
    if (decision === null) {
      pending += 1;
      continue;
    }
    if (decision === "rejected") {
      rejected += 1;
      continue;
    }

    const review = finding.review;
    const category = review?.edited_category?.trim() ? review.edited_category : finding.category;
    items.push({
      findingId: finding.id,
      decision,
      category,
      categoryLabel: categoryDef(category).label,
      importance: review?.edited_importance?.trim() ? review.edited_importance : finding.importance,
      status: review?.edited_status?.trim() ? review.edited_status : finding.status,
      summary: review?.edited_summary?.trim() ? review.edited_summary : finding.summary,
      comment: review?.comment?.trim() || undefined,
    });
  }

  return {
    analysis,
    items,
    decided: analysis.findings.length - pending,
    included: items.length,
    rejected,
    pending,
  };
}

export function statusWord(status: string): string {
  return status.replaceAll("_", " ");
}

export function finalHandoverText(data: FinalHandoverData): string {
  const { analysis, items, rejected, pending, decided } = data;
  const profile = analysis.patient_profile ?? {};
  const lines: string[] = [];

  const field = (label: string, value: unknown) => {
    if (value === undefined || value === null || value === "") return;
    lines.push(`${label}: ${String(value)}`);
  };

  lines.push("FINAL HANDOVER");
  lines.push("===============");
  field("Patient ID", profile.patient_id);
  field("Age / Sex", profile.age != null ? `${profile.age} years · ${profile.sex ?? "–"}` : profile.sex);
  field("Admission date", profile.admission_date);
  field("Reason for admission", profile.admission_reason);
  field("Current location", profile.current_location);
  lines.push("");
  lines.push("HANDOVER");
  lines.push("-------------");
  lines.push(analysis.handover.trim());

  if (items.length > 0) {
    lines.push("");
    lines.push("CLINICALLY IMPORTANT ITEMS TO ADDRESS (clinician-approved)");
    lines.push("---------------------------------------------------------");
    items.forEach((item, index) => {
      lines.push(
        `${index + 1}. [${item.categoryLabel}] (${statusWord(item.status)}, ${item.importance}) ${item.summary}`,
      );
      if (item.decision === "edited") lines.push(`   Reviewer edited: ${DECISION_LABELS.edited}`);
      if (item.comment) lines.push(`   Reviewer comment: ${item.comment}`);
    });
  }
  if (rejected > 0) {
    lines.push("");
    lines.push(`Note: ${rejected} review finding(s) were explicitly rejected and are not included.`);
  }

  lines.push("");
  lines.push(
    `${decided} finding${decided === 1 ? "" : "s"} decided · ${pending} pending. ` +
      "Generated from a human-reviewed AI quality analysis. This is a quality-review aid on synthetic " +
      "demonstration data and must be verified against source records and clinical judgment.",
  );
  return lines.join("\n");
}