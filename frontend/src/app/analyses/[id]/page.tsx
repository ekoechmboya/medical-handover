import type { Metadata } from "next";

import { AnalysisDetailClient } from "@/components/analyses/AnalysisDetailClient";

export const metadata: Metadata = {
  title: "Analysis",
  description: "Full review workspace for a single handover quality analysis.",
};

export default function AnalysisDetailPage() {
  return <AnalysisDetailClient />;
}