# Session Documentation Folder: deployment-configuration
# Primary Session Focus: Test the user's deployed Render backend, switch the frontend API to it, make the deployed backend boot correctly without database/Gemini keys, fix the Vercel (linux) frontend build, and push all changes to GitHub for automatic deploy.

## Session Goal

Make the frontend work against the backend the user deployed to Render (`https://medical-handover.onrender.com`), rather than the local Django server, and leave both services in a state where a plain `git push` triggers working deployments. Concretely: (1) finish verifying the previously built "Final handover" feature, (2) test the deployed backend and diagnose/fix why its data endpoints returned HTTP 500, (3) point the frontend at the deployed URL, (4) confirm the backend can run with no database or API keys set, (5) fix the Vercel frontend build which failed on linux due to a Windows-only SWC package, and (6) commit and push the changes to GitHub.

## Work Completed

1. **Verification of the Final handover feature** (completing the previous session's build). At session start the `/analyses` page appeared stuck in headless Edge. CDP network capture proved no API requests were sent; instead the route `/analyses/[id]/handover` was throwing a server-side `500` (`Cannot find module './vendor-chunks/lucide-react.js'`) because `.next` had been corrupted by running `next build` while the dev server (pid 11220) was running. Stopped the dev server, cleared `node_modules/.cache`, restarted it, and re-verified all three pages in headless Edge via CDP:
   - `/analyses` — "Analysis history", rows `#2`/`#3`, "Open review", per-row "Final handover" button (PASS).
   - `/analyses/2` — Review workspace + Final handover tabs; clicking the "Final handover" radio loaded the assembled document ("Open for receiving clinician", "Copy handover text", "HSP-A48291", allergy item, "Rejected findings are excluded", no "Finish the review") (PASS).
   - `/analyses/2/handover` — "Handover for receiving clinician", "Clinically important items to address", "Print / Save as PDF", "HSP-A48291" (PASS).
   Cleaned up the temporary CDP scripts/profiles.
2. **Tested the deployed backend.** `GET /api/health/` returned 200 (`{"status":"ok","service":"medical-handover-quality-agent"}`). Every data endpoint returned **HTTP 500 `OperationalError: no such table: handovers_analysis`**. The Django DEBUG page revealed: the deployed instance uses the SQLite fallback, `DEBUG=True`, `EMITTER_BACKEND='mock'`, middleware `[config.middleware.DemoCORSMiddleware]`, and that migrations had never run.
3. **Pointed the frontend at the deployed backend.** `frontend/src/lib/api.ts` default changed from `http://127.0.0.1:8000` to `https://medical-handover.onrender.com` (env override `NEXT_PUBLIC_API_BASE_URL` kept); `.env.development` and `.env.example` updated to the same URL with a commented local override. Verified in the browser that requests now go to `medical-handover.onrender.com` (health → "API online", list → backend's 500 shown in the error UI).
4. **Deploy-config fix in repo.** `render.yaml` start command changed to run `python manage.py migrate --noinput && gunicorn ...` at boot, so deployments self-migrate (the earlier `postDeployCommand` never runs on a manually created service).
5. **Brought `backend\.venv` in line with `requirements.txt`** (`pip install -r requirements.txt` installed `dj-database-url 2.3.0`, `gunicorn 23.0.0`, `psycopg/psycopg-binary 3.3.4`, `packaging 26.3`).
6. **Proved the backend runs with no keys (keyless simulation).** Cleared `DATABASE_URL`/`GEMINI_API_KEY`/`MH_EMITTER_BACKEND`/`DJANGO_DEBUG`/`DJANGO_SECRET_KEY` in the shell, temporarily hid the repo `.env`, ran `manage.py migrate --noinput`, booted a second instance on `127.0.0.1:8001`, and exercised the API: health 200, list 200 (`count=5`), create → 201 (`id=8`, `status=completed`), accept review → `review-summary` went from `{total:1,pending:1}` to `{accepted:1,pending:0}`, `Access-Control-Allow-Origin: *`. Cleaned up and restored `.env`.
7. **Supplied the Render environment block** (`GEMINI_API_KEY` read from the repo `.env`, `MH_EMITTER_BACKEND=gemini`, `MH_EMITTER_MODEL=gemini-3.6-flash`, a generated `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`) plus instructions/format for `DATABASE_URL` (the one value that must come from the user's Render Postgres / Supabase dashboard). The user separately stated their backend is "good".
8. **Fixed the Vercel (linux) build failure.** The Vercel log showed `npm error code EBADPLATFORM` / `notsup Unsupported platform for @next/swc-win32-x64-msvc@15.5.24: wanted {"os":"win32","cpu":"x64"} (current: {"os":"linux","cpu":"x64"})`. Removed `@next/swc-win32-x64-msvc` from `frontend/package.json` (it was pinned in a previous session to repair the local native addon), ran `npm install` to refresh the lockfile, and validated `typecheck`, `lint`, and a full production `next build` (all 6 routes) locally.
9. **Pushed to GitHub.** Located `git` at `C:\Program Files\Git\cmd\git.exe` (not on PATH). Only three files were uncommitted (`frontend/package.json`, `frontend/package-lock.json`, `frontend/tsconfig.tsbuildinfo`). Added `frontend/tsconfig.tsbuildinfo` to `.gitignore` and untracked it (`git rm --cached`), committed as `2ec2ea6` and pushed (`ce44ae5..2ec2ea6  main -> main`). Verified `gunit status` is clean and HEAD is `2ec2ea6`. Confirmed via `git check-ignore` that the repo `.env` (Gemini key), `.venv`, and `.next` are properly ignored.

## Important Decisions

- **Frontend default target = deployed backend**, not the local server. The env var `NEXT_PUBLIC_API_BASE_URL` remains the override; production builds ignore `.env.development`, so the code default drives deployed behavior.
- **`render.yaml` must self-migrate at boot** (`startCommand: python manage.py migrate --noinput && gunicorn ...`). A `postDeployCommand` only runs on blueprint-managed services; the observed deployment was configured manually and never migrated.
- **No backend code changes were made** to make the deploy work — existing `settings.py` already falls back to SQLite when `DATABASE_URL` is unset and to the mock emitter when `MH_EMITTER_BACKEND` is unset, and `requirements.txt` already pinned `dj-database-url`/`psycopg[binary]`/`gunicorn`.
- **Keyless operation is explicitly supported.** With no env vars, migrated SQLite + mock emitter serve the full API synchronously (fast demo mode); setting `MH_EMITTER_BACKEND=gemini` + `GEMINI_API_KEY` enables the live model. `DATABASE_URL` is required only for durable/persistent storage.
- **Remove the platform-specific SWC pin** rather than pin the correct one per platform; Next.js already ships per-platform optional dependencies.
- **Untrack the stray build artifact** `frontend/tsconfig.tsbuildinfo` (committed accidentally at some point) and ignore it, instead of shipping its churn.

## Problems Encountered

- `/analyses` (and `/analyses/2`) appeared to hang: "Loading analyses…" persisted in headless Edge; browser `fetch` to the API reported "Failed to fetch" from CDP probes started on `about:blank` (origin `null` → CORS block — probe artifact) and even from `http://localhost:3000`.
- Root cause found via `Network`+`Log` CDP capture: no API request was ever sent because `/analyses/[id]/handover` threw a **server-side 500** — `Uncaught Error: Cannot find module './vendor-chunks/lucide-react.js'` in `.next/server/app/analyses/[id]/handover/page.js` — breaking the whole page tree. Cause: `next build` had been run (previous session) while the dev server was running, corrupting `.next`.
- Deployed backend: `no such table: handovers_analysis` on **all** data endpoints; health OK. DEBUG page showed the manual service had no env vars, SQLite fallback active, DEBUG on, and migrations never run.
- `Invoke-WebRequest` to Render intermittently aborted with "The connection was closed unexpectedly" while `curl.exe` succeeded — a PowerShell/Render response quirk, not a server fault.
- Keyless simulation create returned HTTP 400 once, because the test payload omitted required `patient_profile` fields (`case_id`, `title`, `difficulty`); fixed by mirroring the exact shape in `frontend/src/lib/demo.ts`.
- Vercel build failed with `EBADPLATFORM` for `@next/swc-win32-x64-msvc@15.5.24` on linux.
- `git`, `npm`, `node` not on PATH (PowerShell tool environment); resolved by absolute paths.
- User referenced "you had one already generated that had the password" for the database; no `DATABASE_URL` or Postgres credentials existed anywhere on disk, so the connection string cannot be produced from this machine.

## How They Were Resolved

- Diagnosed with CDP (`cdp_net.cjs`/`cdp_net2.cjs` style probes) capturing `Network.loadingFailed`, `Log.entryAdded`, `Runtime.exceptionThrown`; confirmed fetches to the API return 200 when standalone, isolating the failure to the SSR 500.
- Restarted the Next dev server (with `node_modules/.cache` cleared); verified all pages hydrated correctly afterwards.
- Diagnosed the deployed backend from the public Django DEBUG page (Django 6.1, SQLite vendor, mock emitter, DEBUG=True) and fixed forward via `render.yaml` migrate-at-boot + the env-vars block.
- Used `curl.exe` for Render API testing after PowerShell's client failed.
- Corrected the probe payload to match `DEMO_SCENARIO`'s schema (from the shipped serializer expectations).
- Removed `@next/swc-win32-x64-msvc` from `frontend/package.json`, ran `npm install`, and re-ran `typecheck` / `lint` / `next build` locally until green.
- Found git via `C:\Program Files\Git\cmd\git.exe` and pushed the commit; verified the working tree is clean afterwards.

## Files Changed

- `frontend/src/lib/api.ts` — default base URL now `https://medical-handover.onrender.com`; doc comment updated (env override retained).
- `frontend/.env.development` — `NEXT_PUBLIC_API_BASE_URL=https://medical-handover.onrender.com` (commented local override).
- `frontend/.env.example` — same as above.
- `render.yaml` — `startCommand` now `python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 600 --access-logfile -`.
- `frontend/package.json` — removed `@next/swc-win32-x64-msvc` dependency.
- `frontend/package-lock.json` — regenerated by `npm install`.
- `.gitignore` — added `frontend/tsconfig.tsbuildinfo`; index entry removed via `git rm --cached`.

Files inspected (not modified): `backend/config/settings.py`, `backend/config/middleware.py`, `backend/requirements.txt`, `frontend/src/lib/demo.ts`, `frontend/package.json`, repo `.env` (gitignored; contained only `MH_EMITTER_BACKEND=gemini`, `GEMINI_API_KEY=…`, `MH_EMITTER_MODEL=gemini-3.6-flash` — **no `DATABASE_URL`**).

## Validation Performed

- Headless Edge (CDP) verification: `/analyses` PASS, `/analyses/2` tabs + final-handover tab PASS (`cdp_tabs.cjs`-style, click via `[role="radio"]`), `/analyses/2/handover` PASS.
- Deployed backend: `https://medical-handover.onrender.com/api/health/` → 200; `/api/analyses/` → 500 with `OperationalError: no such table: handovers_analysis` (at the time of testing).
- Local production build: `npm run build` → compiled in ~21s, all 6 routes (`/`, `/_not-found`, `/analyses`, `/analyses/[id]`, `/analyses/[id]/handover`, `/workspace`); `typecheck` and `lint` exit 0.
- Keyless backend simulation on `127.0.0.1:8001` (no `DATABASE_URL`, no `GEMINI_API_KEY`, repo `.env` hidden): health 200; list 200 `count=5`; create 201 `id=8 status=completed`; submit accept review → `review-summary` `{total:1,pending:1}` → `{accepted:1,pending:0}`; CORS `Access-Control-Allow-Origin: *`.
- `pip install -r requirements.txt` → `Successfully installed dj-database-url-2.3.0 gunicorn-23.0.0 packaging-26.3 psycopg-3.3.4 psycopg-binary-3.3.4`.
- Git: `git status` clean; log `2ec2ea6 remove win32 swc dep to fix linux/vercel build; untrack tsbuildinfo` → `ce44ae5 database fix` → `cf2a189 Initial Commit`; push output `ce44ae5..2ec2ea6  main -> main`.
- `.gitignore` verified to cover `.env`, `backend\.venv`, `frontend\.next`.

## Final State

- Local: dev server running on `localhost:3000` pointing at the deployed Render backend; local Django still on `127.0.0.1:8000` (untouched); `backend\.venv` matches `requirements.txt`; repo `.env` restored.
- GitHub: `main` = `2ec2ea6` pushed, clean tree, no secrets tracked.
- Deployed backend: `/api/health/` returns 200. Full data-endpoint correctness on Render after the user's own redeploy/reconfiguration was **not re-verified in-session** (the user stated "backend is good"; only health was re-checked after that point).
- Vercel/GitHub auto-deploy outcomes after the push were **not observed in-session** (no Vercel auth/link on this machine).

## Evidence for Agent Trajectory

- CDP network/console capture (`Network.loadingFailed`, `Log.entryAdded`, `Runtime.exceptionThrown`) that identified the `Cannot find module './vendor-chunks/lucide-react.js'` SSR 500 as the reason pages appeared hung.
- Three-page headless verification results (PASS for `/analyses`, `/analyses/2` tab click, `/analyses/2/handover`), with exact strings checked.
- Public DEBUG-page facts from `https://medical-handover.onrender.com/api/analyses/` (Django 6.1, `OperationalError: no such table: handovers_analysis`, SQLite wrapper, `DEBUG=True`, mock emitter, `DemoCORSMiddleware`) — the basis for the deploy diagnosis.
- Keyless simulation outputs (health/list/create/review/review-summary/CORS on `:8001`) demonstrating env-var-free operation.
- `npm run build` route table and `typecheck`/`lint` exit codes after the SWC removal.
- Git evidence: commit `2ec2ea6`, push ref line `ce44ae5..2ec2ea6`, clean `git status`.