# Session: async backend + google.genai migration (worker-timeout fix)

## What changed

1. **`POST /api/analyses/` is now async.** The engine runs on a daemon thread;
   the endpoint returns `201` immediately with `status="running"` and the
   frontend polls `GET /api/analyses/{id}/` until `completed`/`failed`. Live
   Gemini runs can no longer hit gunicorn's worker timeout (the previous 500).
   `MH_ASYNC=0` restores the old synchronous path (used by the transaction-
   isolated test suite and as a deploy escape hatch).
2. **Per-run backend choice.** `POST /api/analyses/` accepts an optional
   `backend: "mock" | "gemini"` field. Omitted → server-wide
   `MH_EMITTER_BACKEND` env (default `"mock"`) applies. The workspace UI adds a
   "Model backend" toggle; the demo defaults to **offline mock** and only sends
   `backend: "gemini"` when the user picks Live Gemini.
3. **`google.generativeai` → `google.genai`.** The deprecated SDK is replaced in
   `src/medical_handover/llm.py` (`GeminiClient`), with the SDK's built-in retry
   disabled (`HttpRetryOptions(attempts=1)`) and a 30s per-call timeout so the
   caller's paced retry wrapper (`QuotaSafeClient`) stays in control.
   `backend/requirements.txt` and `pyproject.toml` now pin `google-genai>=1.0.0`.
4. **Frontend never aborts a Gemini run.** The old 10-minute create timeout is
   gone; `api.waitForAnalysis()` polls every 2s with no artificial deadline.

## Where the files live

- Backend: `backend/handovers/views.py`, `backend/handovers/serializers.py`,
  `backend/handovers/services/analysis_service.py`, engine client
  `src/medical_handover/llm.py`, deps `backend/requirements.txt`, `pyproject.toml`.
- Frontend: `frontend/src/lib/api.ts`, `frontend/src/types/api.ts`,
  `frontend/src/lib/demo.ts`, `frontend/src/components/workspace/WorkspaceClient.tsx`.
- Tests: `backend/handovers/tests.py` (accounts for the async contract).