import Link from "next/link";
import { ShieldCheck } from "lucide-react";

import BrandMark from "@/components/layout/BrandMark";

export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-white print:hidden">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <BrandMark className="h-8 w-8" />
            <div>
              <p className="text-sm font-semibold tracking-tight">
                Medical Handover Quality Agent
              </p>
              <p className="text-xs text-muted">
                Built for the micro1 Frontier Engineering Challenge.
              </p>
            </div>
          </div>

          <nav
            className="flex items-center gap-6 text-sm text-muted"
            aria-label="Footer"
          >
            <Link href="/workspace" className="transition hover:text-ink">
              Workspace
            </Link>
            <Link href="/analyses" className="transition hover:text-ink">
              Analyses
            </Link>
          </nav>
        </div>

        <div className="mt-8 flex items-start gap-2 rounded-lg border border-line bg-background px-4 py-3 text-xs leading-relaxed text-muted">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-brand-600" aria-hidden="true" />
          <p>
            Engineering demonstration using synthetic data. The agent produces{" "}
            <span className="font-semibold text-ink-soft">candidate findings only</span>
            {" — "}it never performs clinical actions, and a qualified human
            reviewer makes the final decision. Nothing here is clinically
            validated or approved for patient care.
          </p>
        </div>
      </div>
    </footer>
  );
}