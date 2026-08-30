"use client";

import { CircleAlert, RotateCw } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { ApiError } from "@/lib/api";

interface InlineErrorProps {
  title?: string;
  message?: string;
  error?: unknown;
  onRetry?: () => void;
}

export function InlineError({
  title = "Something went wrong",
  message,
  error,
  onRetry,
}: InlineErrorProps) {
  let detail = message;
  if (!detail && error instanceof ApiError) {
    detail = error.detail;
    if (error.status === 0) {
      detail = `${error.detail} The API status badge in the header can help confirm connectivity.`;
    }
  }
  if (!detail && error instanceof Error && error.message) {
    detail = error.message;
  }
  if (!detail) {
    detail = "An unexpected error occurred.";
  }

  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-5 py-4"
    >
      <div className="flex items-center gap-2 text-rose-800">
        <CircleAlert className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span className="text-sm font-semibold">{title}</span>
      </div>
      <p className="text-sm leading-relaxed text-rose-900">{detail}</p>
      {onRetry ? (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          <RotateCw className="h-3.5 w-3.5" aria-hidden="true" />
          Try again
        </Button>
      ) : null}
    </div>
  );
}