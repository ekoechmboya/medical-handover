"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export interface SegmentOption {
  value: string;
  label: ReactNode;
  description?: ReactNode;
  icon?: ReactNode;
}

interface SegmentedControlProps {
  options: SegmentOption[];
  value: string;
  onChange: (value: string) => void;
  name: string;
  className?: string;
}

/**
 * Premium segmented control with an animated thumb. Behaves like a radio group
 * for assistive technology.
 */
export function SegmentedControl({
  options,
  value,
  onChange,
  name,
  className,
}: SegmentedControlProps) {
  return (
    <div
      role="radiogroup"
      aria-label={name}
      className={cn(
        "grid rounded-xl border border-line bg-background p-1",
        className,
      )}
      style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}
    >
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option.value)}
            className={cn(
              "relative flex flex-col items-center justify-center gap-1 rounded-lg px-3 py-3 text-center outline-none transition-colors focus-visible:ring-2 focus-visible:ring-brand-600",
              selected ? "text-brand-900" : "text-muted hover:text-ink",
            )}
          >
            {selected ? (
              <motion.span
                layoutId={`segment-${name}`}
                transition={{ type: "spring", stiffness: 500, damping: 38 }}
                className="absolute inset-0 rounded-lg border border-line bg-white shadow-sm"
                aria-hidden="true"
              />
            ) : null}
            <span className="relative flex flex-col items-center gap-1">
              {option.icon ? (
                <span className="[&>svg]:h-4 [&>svg]:w-4">{option.icon}</span>
              ) : null}
              <span className="text-sm font-semibold">{option.label}</span>
              {option.description ? (
                <span className="text-[11px] font-normal leading-snug text-muted">
                  {option.description}
                </span>
              ) : null}
            </span>
          </button>
        );
      })}
    </div>
  );
}