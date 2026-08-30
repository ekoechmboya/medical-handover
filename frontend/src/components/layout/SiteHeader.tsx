"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ClipboardCheck } from "lucide-react";

import BrandMark from "@/components/layout/BrandMark";
import { BackendStatus } from "@/components/layout/BackendStatus";

const NAV_LINKS = [
  { href: "/", label: "Overview" },
  { href: "/workspace", label: "Workspace" },
  { href: "/analyses", label: "Analyses" },
];

export function SiteHeader() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-background/85 backdrop-blur-md print:hidden">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link
          href="/"
          className="group flex items-center gap-2.5 rounded-md"
          aria-label="Medical Handover Quality Agent — home"
        >
          <BrandMark />
          <span className="hidden flex-col leading-tight sm:flex">
            <span className="text-sm font-semibold tracking-tight">
              Handover Quality Agent
            </span>
            <span className="text-[11px] font-medium text-muted">
              Human-in-the-loop clinical handover review
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
          {NAV_LINKS.map((link) => {
            const active = isActive(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-brand-50 text-brand-800"
                    : "text-muted hover:bg-white hover:text-ink"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3">
          <div className="hidden sm:block">
            <BackendStatus />
          </div>
          <Link
            href="/workspace"
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-700 px-3 py-1.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-800"
          >
            <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
            Open Analysis Workspace
          </Link>
        </div>
      </div>
    </header>
  );
}