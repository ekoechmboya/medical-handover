import type { Metadata } from "next";

import { LandingPage } from "@/components/landing/LandingPage";

export const metadata: Metadata = {
  title: "Medical Handover Quality Agent",
  description:
    "Agentic AI for clinical handover quality review — candidate findings, evidence, verification, and human oversight.",
};

export default function HomePage() {
  return <LandingPage />;
}