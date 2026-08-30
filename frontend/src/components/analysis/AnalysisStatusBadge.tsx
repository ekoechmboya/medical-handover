import { CheckCircle2, CircleAlert, Clock, LoaderCircle } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { AnalysisStatus } from "@/types/api";

const STATUS_META: Record<AnalysisStatus, { label: string; tone: "slate" | "sky" | "emerald" | "rose"; icon: typeof LoaderCircle }> = {
  pending: { label: "Pending", tone: "slate", icon: Clock },
  running: { label: "Running", tone: "sky", icon: LoaderCircle },
  completed: { label: "Completed", tone: "emerald", icon: CheckCircle2 },
  failed: { label: "Failed", tone: "rose", icon: CircleAlert },
};

export function AnalysisStatusBadge({ status }: { status: AnalysisStatus }) {
  const meta = STATUS_META[status];
  const Icon = meta.icon;
  return (
    <Badge tone={meta.tone} icon={<Icon aria-hidden="true" />} title={`Analysis status: ${meta.label}`}>
      {meta.label}
    </Badge>
  );
}