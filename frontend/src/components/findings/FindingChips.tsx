import { Badge } from "@/components/ui/Badge";
import type { Tone } from "@/components/ui/tone";
import {
  categoryDef,
  IMPORTANCE_DEFS,
  STATUS_DEFS,
} from "@/lib/constants";
import type { Importance } from "@/types/api";

export function CategoryBadge({ category }: { category: string }) {
  const def = categoryDef(category);
  const Icon = def.icon;
  return (
    <Badge tone={def.tone as Tone} icon={<Icon aria-hidden="true" />} title={`Category: ${def.label}`}>
      {def.label}
    </Badge>
  );
}

export function ImportanceBadge({ importance }: { importance: string }) {
  const def = IMPORTANCE_DEFS[importance as Importance] ?? {
    label: importance,
    icon: null,
    tone: "slate" as Tone,
  };
  const Icon = def.icon;
  return (
    <Badge tone={def.tone} icon={Icon ? <Icon aria-hidden="true" /> : undefined} title={`Importance: ${def.label}`}>
      {def.label}
    </Badge>
  );
}

export function FindingStatusBadge({ status }: { status: string }) {
  const def = STATUS_DEFS[status] ?? {
    label: status.replaceAll("_", " "),
    icon: null,
    tone: "slate" as Tone,
    hint: "",
  };
  const Icon = def.icon as React.ElementType | null;
  return (
    <Badge
      tone={def.tone as Tone}
      icon={Icon ? <Icon aria-hidden="true" /> : undefined}
      title={`${def.label} — ${def.hint}`}
    >
      {def.label}
    </Badge>
  );
}