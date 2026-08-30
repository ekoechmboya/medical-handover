import type { Metadata } from "next";

import { ReceivingClinic } from "@/components/handover/ReceivingClinic";

export const metadata: Metadata = {
  title: "Final handover",
  description:
    "Print-ready final handover for the receiving clinician, assembled from the reviewed analysis.",
};

export default function FinalHandoverPage() {
  return <ReceivingClinic />;
}