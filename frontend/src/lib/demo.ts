/**
 * Synthetic demonstration scenario used by the "Load Demo Scenario" action in
 * the analysis workspace. The content is deliberately crafted so the
 * deterministic mock engine (and a live model) surfaces a broad spread of
 * finding categories without requiring a reviewer to type clinical text.
 *
 * All data is fictional and clearly labelled as synthetic in the UI.
 */

import type { AnalysisInput } from "@/types/api";

export const DEMO_SCENARIO: Omit<AnalysisInput, "mode"> = {
  patient_profile: {
    case_id: "demo_syn_01",
    title: "Synthetic demo — omitted clinical detail",
    difficulty: "easy",
    patient_id: "HSP-A48291",
    age: 64,
    sex: "F",
    admission_reason: "Community-acquired pneumonia",
    current_location: "Medical Ward A · Bay 3",
    admission_date: "2026-08-27",
  },
  records: [
    {
      filename: "admission_note.txt",
      content:
        "Admission Note - 2026-08-27 21:05\n" +
        "Patient admitted with community-acquired pneumonia affecting the right lower lobe.\n" +
        "The patient has a documented severe penicillin allergy and experienced anaphylaxis in the past.\n" +
        "Started on anticoagulation with enoxaparin 40mg subcutaneously once daily for VTE prophylaxis.\n" +
        "Fall risk is high and mobility requires one to one supervision.",
    },
    {
      filename: "progress_note.txt",
      content:
        "Progress Note - 2026-08-28 07:40\n" +
        "Oxygen saturation target is greater than 94 percent and current readings are borderline.\n" +
        "The patient should be escalated urgently if the GCS drops below 12.\n" +
        "Blood cultures remain pending from the sample drawn at admission.\n" +
        "Mental status: confused overnight and disoriented to place.",
    },
    {
      filename: "consults.txt",
      content:
        "Consultation Log - 2026-08-28\n" +
        "The infectious diseases specialist will review the patient this afternoon.",
    },
  ],
  handover:
    "The patient remains comfortable on the current care plan. Observations are due again at the next shift.",
};

export const DEMO_LABEL = "Synthetic demonstration data";