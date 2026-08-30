import { Cpu, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { Mode } from "@/types/api";

export function ModeBadge({ mode, size = "md" }: { mode: Mode; size?: "sm" | "md" }) {
  if (mode === "advanced") {
    return (
      <Badge
        tone="brand"
        icon={<Sparkles aria-hidden="true" />}
        className={size === "sm" ? "px-2 text-[11px]" : ""}
        title="Advanced agentic pipeline: generation, verification, detail probing, reconciliation and deduplication."
      >
        Advanced Agent
      </Badge>
    );
  }
  return (
    <Badge
      tone="slate"
      icon={<Cpu aria-hidden="true" />}
      className={size === "sm" ? "px-2 text-[11px]" : ""}
      title="Baseline: single-pass AI analysis."
    >
      Baseline
    </Badge>
  );
}