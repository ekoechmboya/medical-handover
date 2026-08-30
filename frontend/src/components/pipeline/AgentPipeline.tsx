import { ArrowRight } from "lucide-react";

import { ADVANCED_STAGES } from "@/lib/constants";
import { cn } from "@/lib/cn";

const STAGE_DEFS = new Map(ADVANCED_STAGES.map((stage) => [stage.key, stage]));

export interface AgentPipelineProps {
  /** Pipeline stage keys, e.g. ["generate","verify","detail","reconcile","dedup"]. */
  stages: string[];
  /** Highlight the stage currently being executed (running state). */
  activeIndex?: number;
  compact?: boolean;
  className?: string;
}

/**
 * Visualises the agent pipeline stages. Used on the landing page, the analysis
 * detail page and the workspace running state.
 */
export function AgentPipeline({
  stages,
  activeIndex,
  compact,
  className,
}: AgentPipelineProps) {
  const defs = stages.map((key) => STAGE_DEFS.get(key)).filter(Boolean);

  return (
    <ol
      className={cn(
        "flex flex-wrap items-center gap-y-2",
        compact ? "gap-x-1.5" : "gap-x-2",
        className,
      )}
    >
      {defs.map((def, index) => {
        const Icon = def!.icon;
        const active = activeIndex === index;
        return (
          <li key={def!.key} className="flex items-center gap-x-1.5 sm:gap-x-2">
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-lg border font-medium transition-colors",
                compact ? "px-2 py-1 text-[11px]" : "px-2.5 py-1.5 text-xs",
                active
                  ? "border-brand-500 bg-brand-50 text-brand-800"
                  : "border-line bg-white text-ink-soft",
              )}
              title={def!.description}
            >
              <Icon className={cn("shrink-0", compact ? "h-3 w-3" : "h-3.5 w-3.5")} aria-hidden="true" />
              <span className={cn(active && "animate-soft-pulse font-semibold")}>
                {def!.label}
              </span>
              {active ? <span className="sr-only">(in progress)</span> : null}
            </span>
            {index < defs.length - 1 ? (
              <ArrowRight
                className={cn("shrink-0 text-faint", compact ? "h-3 w-3" : "h-3.5 w-3.5")}
                aria-hidden="true"
              />
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}