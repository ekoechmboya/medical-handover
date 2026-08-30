import { useState } from "react";
import { motion } from "framer-motion";
import { ChevronDown, FileText } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { FindingEvidence } from "@/types/api";
import { cn } from "@/lib/cn";

export function EvidenceItem({
  evidence,
  defaultExpanded = false,
}: {
  evidence: FindingEvidence;
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className="overflow-hidden rounded-lg border border-line bg-background/60">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className={cn(
          "flex w-full items-center justify-between gap-3 px-3 py-2 text-left transition hover:bg-slate-100/70",
        )}
      >
        <span className="flex min-w-0 items-center gap-2">
          <FileText className="h-3.5 w-3.5 shrink-0 text-muted" aria-hidden="true" />
          <span className="truncate font-mono text-xs font-medium text-ink-soft">
            {evidence.filename}
          </span>
        </span>
        <span className="flex shrink-0 items-center gap-1.5 text-xs text-muted">
          <span>source</span>
          <ChevronDown
            className={cn("h-3.5 w-3.5 transition-transform", expanded && "rotate-180")}
            aria-hidden="true"
          />
        </span>
      </button>
      {expanded ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="border-t border-line px-3 py-2.5"
        >
          <p className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-ink-soft">
            {evidence.content}
          </p>
        </motion.div>
      ) : null}
    </div>
  );
}

export function EvidenceList({
  evidence,
  sourceNames,
}: {
  evidence: FindingEvidence[];
  sourceNames: string[];
}) {
  const resolvedNames = new Set(evidence.map((e) => e.filename));
  const unresolved = sourceNames.filter((name) => !resolvedNames.has(name));

  if (evidence.length === 0 && unresolved.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      {evidence.map((item) => (
        <EvidenceItem key={item.filename} evidence={item} />
      ))}
      {unresolved.length > 0 ? (
        <div className="flex flex-wrap gap-1.5 px-0.5 pt-1">
          {unresolved.map((name) => (
            <Badge key={name} tone="slate" className="font-mono text-[11px]">
              {name}
            </Badge>
          ))}
        </div>
      ) : null}
    </div>
  );
}