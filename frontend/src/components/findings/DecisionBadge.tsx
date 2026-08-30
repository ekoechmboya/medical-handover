import { Badge } from "@/components/ui/Badge";
import { DECISION_DEFS } from "@/lib/constants";
import type { ReviewDecision } from "@/types/api";

export function DecisionBadge({ decision }: { decision: ReviewDecision }) {
  const def = DECISION_DEFS[decision];
  const Icon = def.icon;
  return (
    <Badge tone={def.tone} icon={<Icon aria-hidden="true" />}>
      {def.label}
    </Badge>
  );
}