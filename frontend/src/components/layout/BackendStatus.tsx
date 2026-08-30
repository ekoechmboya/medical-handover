"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, CircleAlert, LoaderCircle, RefreshCw } from "lucide-react";

import { api } from "@/lib/api";

type Status = "checking" | "online" | "offline";

export function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [retryKey, setRetryKey] = useState(0);

  const check = useCallback(async () => {
    setStatus("checking");
    try {
      await api.health();
      setStatus("online");
    } catch {
      setStatus("offline");
    }
  }, []);

  useEffect(() => {
    void check();
  }, [check, retryKey]);

  if (status === "checking") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-white px-2.5 py-1 text-xs font-medium text-muted">
        <LoaderCircle className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
        Checking API…
      </span>
    );
  }

  if (status === "online") {
    return (
      <span
        className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800"
        title="API backend is reachable"
      >
        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
        API online
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setRetryKey((k) => k + 1)}
      className="inline-flex items-center gap-1.5 rounded-full border border-rose-200 bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-800 transition hover:bg-rose-100"
      title="Backend not reachable — click to retry"
    >
      <CircleAlert className="h-3.5 w-3.5" aria-hidden="true" />
      API offline
      <RefreshCw className="h-3 w-3" aria-hidden="true" />
    </button>
  );
}