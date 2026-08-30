"use client";

import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import type { ReactNode } from "react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  description?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  labelledBy?: string;
}

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  labelledBy,
}: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          role="dialog"
          aria-modal="true"
          aria-labelledby={labelledBy}
        >
          <div
            className="absolute inset-0 bg-slate-950/40 backdrop-blur-[2px]"
            onClick={onClose}
            aria-hidden="true"
          />
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.98 }}
            transition={{ duration: 0.18, ease: [0.4, 0, 0.2, 1] }}
            className="relative flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-t-2xl border border-line bg-white shadow-2xl sm:rounded-2xl"
          >
            <div className="flex items-start justify-between gap-4 border-b border-line px-6 py-4">
              <div>
                <h2 id={labelledBy} className="text-base font-semibold tracking-tight">
                  {title}
                </h2>
                {description ? (
                  <p className="mt-0.5 text-sm text-muted">{description}</p>
                ) : null}
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close dialog"
                className="rounded-md p-1.5 text-muted transition hover:bg-slate-100 hover:text-ink"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5 scrollbars-thin">
              {children}
            </div>
            {footer ? (
              <div className="flex justify-end gap-2 border-t border-line bg-background px-6 py-4">
                {footer}
              </div>
            ) : null}
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}