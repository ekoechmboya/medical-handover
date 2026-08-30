# Improvement Changelog Entry — async backend + google.genai migration

## Problem or hypothesis

Render logs showed `WORKER TIMEOUT` on `POST /api/analyses/`: gunicorn's 600s
inactivity timeout fired while the synchronous advanced pipeline was mid-call on
the live Gemini emitter (`analysis_service` → `pipeline.probe_details` →
`detail_probe.complete_json` → `QuotaSafeClient.time.sleep`), aborting the worker
and returning 500. Hypothesis (confirmed): a multi-minute, request-bound Gemini
run cannot fit a synchronous web request on Render free, and the SDK in use
(`google.generativeai`) is deprecated, emitting a startup warning.

## What was tried

1. Read `analysis_service.py` (`QuotaSafeClient`: ≥5s pacing + 20–65s retry
   sleeps) and `src/medical_handover/llm.py` (deprecated `google.generativeai`,
   `google.api_core.retry.Retry(max_attempts=1)`, 30s call timeout).
2. Migrated `GeminiClient` to `google.genai` (installed `google-genai 2.20.0`),
   disabling SDK retries via `HttpRetryOptions(attempts=1)` and keeping the 30s
   per-call timeout; updated `requirements.txt` + the `llm` extra in `pyproject`.
3. Made the create endpoint async: row created as `running`, engine run on a
   daemon thread (`close_old_connections`-guarded), `MH_ASYNC=0` fallback.
4. Added per-request `backend` override (mock/gemini); omitted → env fallback.
5. Frontend: `createAnalysis` returns immediately (60s guard), new
   `waitForAnalysis(id)` polls every 2s with no deadline; workspace gains a
   "Model backend" toggle defaulting to offline mock; copy explains that a
   Gemini run "waits until it finishes — no timeout".
6. Kept tests deterministic: suite forces `MH_ASYNC=0` (Django `TestCase`
   transactions are invisible to other connections); new async test re-enables
   `MH_ASYNC=1`; the gems-branch test forces `GEMINI_API_KEY=""` so it fails at
   client construction with no network/quota use.

## Why this approach was chosen

- Async decouples engine runtime from web-request budget: the same API and frontend
  work for instant mock runs and minutes-long live runs without timeouts.
- Per-run backend choice keeps the public demo offline and reliable by default
  while making Live Gemini an explicit, opt-in showcase (per user decision).
- `google.genai` is the maintained SDK (removes the deprecation warning); SDK
  retries are disabled so `QuotaSafeClient`/`RateLimitedClient` remain the only
  retry authority (avoids free-tier retry storms).
- The env gate + optional field preserve the previous deploy contract
  (`MH_EMITTER_BACKEND=gemini` still works server-wide for non-UI clients).

## What happened

- Backend health + async contract verified locally: POST returns
  `running` (≈2.7s) then poll #1 → `completed`, 3 findings, `backend=mock`.
- Frontend `typecheck`, `lint`, and `next build` all green (6 routes).
- `backend/handovers/tests.py` updated for the new contract.

## Evidence or validation

- Render log (prior): `WORKER TIMEOUT` with traceback through
  `handovers/views.py:67` → `analysis_service.py:209 run_pipeline` →
  `pipeline.py:101 probe_details` → `detail_probe.py:62 client.complete_json` →
  `analysis_service.py:70 time.sleep(wait)`; worker aborted → SIGKILL summary.
- Deprecation warning at import: `google.generativeai` → use `google.genai`.
- Local smoke (async): `POST_MS=2730 ID=2 STATUS=running FINDINGS=0` →
  `POLLS=1 TERMINAL=completed FINDINGS=3 BACKEND=mock ERR=`.
- SDK capability probe: `genai.Client(api_key=...)`,
  `GenerateContentConfig(temperature, response_mime_type, http_options)`,
  `HttpOptions(timeout, retry_options=HttpRetryOptions(attempts=1))`.

## Decision or next step

Deploy both changes (push to `main` so Vercel/Render rebuild); keep the demo
defaulting to offline mock. Optional follow-ups: a proper queue/worker if a
long-lived archived run store is needed, and re-verify the full UI flow
(workspace → poll → review → final handover) against the deployed endpoint
with a live Gemini run.