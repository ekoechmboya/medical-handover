/** Tailwind class buckets for the tone system used by badges and accents. */

export type Tone =
  | "slate"
  | "brand"
  | "amber"
  | "orange"
  | "emerald"
  | "rose"
  | "violet"
  | "sky"
  | "indigo"
  | "cyan"
  | "teal"
  | "blue";

export const TONE_BADGE: Record<Tone, string> = {
  slate: "border-slate-200 bg-slate-100 text-slate-700",
  brand: "border-brand-200 bg-brand-50 text-brand-800",
  amber: "border-amber-200 bg-amber-50 text-amber-800",
  orange: "border-orange-200 bg-orange-50 text-orange-800",
  emerald: "border-emerald-200 bg-emerald-50 text-emerald-800",
  rose: "border-rose-200 bg-rose-50 text-rose-800",
  violet: "border-violet-200 bg-violet-50 text-violet-800",
  sky: "border-sky-200 bg-sky-50 text-sky-800",
  indigo: "border-indigo-200 bg-indigo-50 text-indigo-800",
  cyan: "border-cyan-200 bg-cyan-50 text-cyan-800",
  teal: "border-teal-200 bg-teal-50 text-teal-800",
  blue: "border-blue-200 bg-blue-50 text-blue-800",
};

export const TONE_DOT: Record<Tone, string> = {
  slate: "bg-slate-400",
  brand: "bg-brand-600",
  amber: "bg-amber-500",
  orange: "bg-orange-500",
  emerald: "bg-emerald-500",
  rose: "bg-rose-500",
  violet: "bg-violet-500",
  sky: "bg-sky-500",
  indigo: "bg-indigo-500",
  cyan: "bg-cyan-500",
  teal: "bg-teal-500",
  blue: "bg-blue-500",
};

export const TONE_TEXT: Record<Tone, string> = {
  slate: "text-slate-600",
  brand: "text-brand-700",
  amber: "text-amber-700",
  orange: "text-orange-700",
  emerald: "text-emerald-700",
  rose: "text-rose-700",
  violet: "text-violet-700",
  sky: "text-sky-700",
  indigo: "text-indigo-700",
  cyan: "text-cyan-700",
  teal: "text-teal-700",
  blue: "text-blue-700",
};

export const TONE_SOLID: Record<Tone, string> = {
  slate: "bg-slate-700 text-white",
  brand: "bg-brand-700 text-white",
  amber: "bg-amber-600 text-white",
  orange: "bg-orange-600 text-white",
  emerald: "bg-emerald-600 text-white",
  rose: "bg-rose-600 text-white",
  violet: "bg-violet-600 text-white",
  sky: "bg-sky-600 text-white",
  indigo: "bg-indigo-600 text-white",
  cyan: "bg-cyan-600 text-white",
  teal: "bg-teal-600 text-white",
  blue: "bg-blue-600 text-white",
};