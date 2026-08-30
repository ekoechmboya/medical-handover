import type { Metadata } from "next";

import { WorkspaceClient } from "@/components/workspace/WorkspaceClient";

export const metadata: Metadata = {
  title: "Analysis Workspace",
  description:
    "Run a handover quality analysis — baseline or advanced agent — and review the candidate findings.",
};

export default function WorkspacePage() {
  return <WorkspaceClient />;
}