# Evidence — async backend + google.genai migration

## Incident reproduction (deployed Render log, before the fix)

```
[CRITICAL] WORKER TIMEOUT (pid:41)
File "/opt/render/project/src/backend/handovers/views.py", line 67, in post ... run_analysis
File "/opt/render/project/src/backend/handovers/services/analysis_service.py", line 209 ... run_pipeline(case, client, enabled=set(ADVANCED_STAGES))
File ".../src/medical_handover/agent/pipeline.py", line 101 ... probe_details
File ".../src/medical_handover/agent/detail_probe.py", line 62 ... client.complete_json(prompt)
File ".../backend/handovers/services/analysis_service.py", line 70 ... time.sleep(wait)
SystemExit: 3 (worker aborted ... SIGKILL)
```
Plus startup deprecation: importing `google.generativeai` in favour of `google.genai`.

## Migration check (google-genai 2.20.0, installed into backend/.venv)

- `genai.Client(api_key=...)` accepted; `http_options: HttpOptions | HttpOptionsDict`.
- `HttpOptions` fields include `timeout` (ms) and
  `retry_options=HttpRetryOptions(attempts, initial_delay, max_delay, ...)`.
- `client.models.generate_content(model=..., contents=..., config=GenerateContentConfig(...))`
  with `temperature`, `response_mime_type`, `http_options` all present.
- Used: `HttpOptions(timeout=30_000, retry_options=HttpRetryOptions(attempts=1))`.

## Local async smoke (single dev instance on 127.0.0.1:8000)

```
POST_MS=2730 ID=2 STATUS=running FINDINGS=0      # POST body included backend:"mock"
POLLS=1 TERMINAL=completed FINDINGS=3 BACKEND=mock ERR=
```
POST returns `201` immediately as `running`; polling GET reaches `completed`.

## Backend tests (28 collected, currently re-run after empty-key fix)

- Suite forces `MH_EMITTER_BACKEND=mock` + `MH_ASYNC=0` at class level.
- Adjusted/added: async-contract test (`MH_ASYNC=1`: POST → `running`, empty
  findings, engine_meta `{}`), per-request backend test (`backend:"gemini"` +
  empty key → `failed`, `engine_meta.backend=="gemini"`), invalid-backend 400,
  and the pre-existing env-driven failure test (restored by making the
  `backend` field optional, falling back to `MH_EMITTER_BACKEND`).

## Frontend validation

- `npm run typecheck` → exit 0. `npm run lint` → exit 0.
- `npm run build` → green; routes: `/`, `/analyses`, `/analyses/[id]`,
  `/analyses/[id]/handover`, `/workspace`; first-load JS 155–169 kB.

## Relevant file set (this session)

- `src/medical_handover/llm.py`, `backend/handovers/views.py`,
  `backend/handovers/serializers.py`, `backend/handovers/services/analysis_service.py`,
  `backend/handovers/tests.py`, `backend/requirements.txt`, `pyproject.toml`.
- `frontend/src/lib/api.ts`, `frontend/src/types/api.ts`,
  `frontend/src/lib/demo.ts`, `frontend/src/components/workspace/WorkspaceClient.tsx`.