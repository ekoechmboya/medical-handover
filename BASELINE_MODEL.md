# Pinned Baseline Model

**Baseline model (pinned): `gemini-3.6-flash`** (temperature 0.0)

This model is used for **both** the one-shot baseline and the advanced agent so
the Milestone 2 → Milestone 3 comparison measures *agentic engineering*, not
model capability. Do not change the model to manufacture an artificial
improvement.

## Why this model (and not the originally planned ones)

The originally planned Gemini models were unavailable on this account at run
time (verified 2026-08-29):

| Requested       | Result                                                        |
|-----------------|---------------------------------------------------------------|
| `gemini-1.5-flash` | `404 ... is not found for API version v1beta` (deprecated) |
| `gemini-2.5-flash` | `404 ... no longer available to new users` (use 3.6-flash)  |

`gemini-3.6-flash` is the available, pinned substitute. It is referenced from:
- `src/medical_handover/llm.py::BASELINE_MODEL` (code default)
- `.env` (`MH_EMITTER_MODEL=gemini-3.6-flash`) for the run scripts

## How to reproduce the baseline

```powershell
.venv\Scripts\python.exe run_real_baseline.py
```

The key is read from the gitignored `.env` (`GEMINI_API_KEY=...`). Ground truth
is opened **only after** Gemini returns findings; it is never sent to the model.

## Evidence (do not overwrite)

- `reports/gemini_baseline_20260829_110323/baseline_results.json` — master results
- `reports/gemini_baseline_20260829_110323/prompts/<case>.txt` — exact prompts sent
- `reports/gemini_baseline_20260829_110323/responses/<case>.json` — raw model payloads

Headline baseline numbers (15 cases, macro-mean per case):
recall 0.970 · precision 0.754 · F1 0.829 · importance_recall 0.966 ·
status_accuracy 0.833 · false alarms (FP) 11 · false negatives 2 ·
runtime 243.1s · ~14,807 tokens · est. cost $0.0038.
