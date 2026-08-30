import Link from "next/link";
import type { ReactNode } from "react";
import { LoaderCircle } from "lucide-react";

import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "success";
type Size = "sm" | "md" | "lg";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-brand-700 text-white border-transparent shadow-sm hover:bg-brand-800 focus-visible:ring-brand-600 disabled:bg-brand-300",
  secondary:
    "bg-white text-ink border-line hover:border-line-strong hover:bg-slate-50 focus-visible:ring-brand-500 disabled:text-muted",
  ghost:
    "bg-transparent text-muted border-transparent hover:bg-slate-100 hover:text-ink focus-visible:ring-brand-500 disabled:text-faint",
  danger:
    "bg-rose-600 text-white border-transparent shadow-sm hover:bg-rose-700 focus-visible:ring-rose-600 disabled:bg-rose-300",
  success:
    "bg-emerald-700 text-white border-transparent shadow-sm hover:bg-emerald-800 focus-visible:ring-emerald-600 disabled:bg-emerald-300",
};

const SIZES: Record<Size, string> = {
  sm: "h-8 px-3 text-sm gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
  lg: "h-12 px-5 text-base gap-2",
};

interface ButtonProps {
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  type?: "button" | "submit";
  disabled?: boolean;
  loading?: boolean;
  href?: string;
  onClick?: () => void;
  className?: string;
  title?: string;
  "aria-label"?: string;
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  type = "button",
  disabled,
  loading,
  href,
  onClick,
  className,
  title,
  ...rest
}: ButtonProps) {
  const classes = cn(
    "inline-flex items-center justify-center rounded-lg border font-semibold transition-colors",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
    VARIANTS[variant],
    SIZES[size],
    disabled && "pointer-events-none opacity-70",
    className,
  );
  const content = (
    <>
      {loading ? (
        <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
      ) : null}
      {children}
    </>
  );

  if (href) {
    return (
      <Link href={href} className={classes} title={title} {...rest}>
        {content}
      </Link>
    );
  }

  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className={classes}
      title={title}
      {...rest}
    >
      {content}
    </button>
  );
}