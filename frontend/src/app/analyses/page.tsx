import type { Metadata } from "next";

import { AnalysesClient } from "@/components/analyses/AnalysesClient";

export const metadata: Metadata = {
  title: "Analysis History",
  description:
    "Previous handover quality analyses with findings, modes, and human review progress.",
};

export default function AnalysesPage() {
  return <AnalysesClient />;
}