# Evidence — deployment-configuration

Verifiable artifacts from this OpenCode session. Secret values (Gemini API key, generated Django secret) are intentionally **not reproduced** here.

## Important prompts / instructions

- "https://medical-handover.onrender.com/ this is where i have deployed my backend, you can test it and update the frontend to use it" — triggered backend testing + frontend API switch.
- "so i need to redeploy without setting database keys or api keys on environment variables on render" — led to the migrate-at-boot change and the keyless simulation.
- "you had one already generated that had the password" — led to an exhaustive disk search (repo + temp) for an existing Postgres connection string; none found.
- User-pasted error page text: `OperationalError at /api/analyses — no such table: handovers_analysis`, `Django Version: 6.1`, exception location `django/db/backends/sqlite3/base.py`, and Vercel log: `npm error code EBADPLATFORM ... Unsupported platform for @next/swc-win32-x64-msvc@15.5.24: wanted {"os":"win32","cpu":"x64"} (current: {"os":"linux","cpu":"x64"})`.
- "backend is good, deploy to reflect what is on frontend" and "deploy the changes to github, it will take it from there" — terminal deployment instructions.

## Files inspected

- `frontend/src/lib/api.ts` — base URL resolution via `NEXT_PUBLIC_API_BASE_URL` with fallback; default was `http://127.0.0.1:8000` (line 18 pre-edit).
- `backend/config/middleware.py` — `DemoCORSMiddleware` sets `Access-Control-Allow-Origin: *`, methods `GET, POST, OPTIONS`, headers `Content-Type, Accept, Origin`, max-age 86400.
- `backend/config/settings.py` — `DATABASES` via `dj_database_url.config(default=f"sqlite:///{BASE_DIR/'db.sqlite3'}", conn_max_age=60)` (SQLite fallback when `DATABASE_URL` unset); `DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"`; `EMITTER_BACKEND = os.environ.get("MH_EMITTER_BACKEND", "mock")`; loads `REPO_ROOT/.env` with `setdefault`.
- `backend/requirements.txt` — `django>=6.1,<7`, `djangorestframework>=3.18,<4`, `google-generativeai>=0.7.0`, `dj-database-url>=2.1,<3`, `psycopg[binary]>=3.1,<4`, `gunicorn>=21,<24`.
- `frontend/src/lib/demo.ts` — exact `AnalysisInput` shape (`patient_profile` requires `case_id`, `title`, `difficulty`, …; `records[]`; `handover` string).
- Repo `.env` (gitignored) via temporary rename — contained exactly: `MH_EMITTER_BACKEND=gemini`, `GEMINI_API_KEY=AQ.Ab8…` (value not reproduced), `MH_EMITTER_MODEL=gemini-3.6-flash`. **No `DATABASE_URL` present.**

## Files created or modified

| Path | Change |
|---|---|
| `frontend/src/lib/api.ts` | `DEFAULT_API_BASE_URL` → `https://medical-handover.onrender.com`; comment updated |
| `frontend/.env.development` | `NEXT_PUBLIC_API_BASE_URL=https://medical-handover.onrender.com` (+commented local override) |
| `frontend/.env.example` | same as above |
| `render.yaml` | `startCommand: python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 600 --access-logfile -` |
| `frontend/package.json` | removed `@next/swc-win32-x64-msvc` |
| `frontend/package-lock.json` | regenerated (`npm install`) |
| `.gitignore` | added `frontend/tsconfig.tsbuildinfo` |

## Notable terminal commands

- `curl.exe -s -o <file> -w "list HTTP %{http_code} size %{size_download}\n" --max-time 120 "https://medical-handover.onrender.com/api/analyses/"` → `health HTTP 000` once, then `list HTTP 500 size 162434`.
- `python -m pip install -r requirements.txt` (in `backend` venv) → `Successfully installed dj-database-url-2.3.0 gunicorn-23.0.0 packaging-26.3 psycopg-3.3.4 psycopg-binary-3.3.4`.
- Keyless sim: `Remove-Item Env:DATABASE_URL,Env:GEMINI_API_KEY,Env:MH_EMITTER_BACKEND,Env:DJANGO_DEBUG,Env:DJANGO_SECRET_KEY`; rename `.env` → `.env.keylessbak`; `manage.py migrate --noinput` → `No migrations to apply`; `manage.py runserver 127.0.0.1:8001 --noreload` (pid 13296).
- `npm.cmd run typecheck` (exit 0), `npm.cmd run lint` (exit 0), `npm.cmd run build` (exit 0).
- `"C:\Program Files\Git\cmd\git.exe"` for all git ops; `git push origin main` → `ce44ae5..2ec2ea6  main -> main`.

## Errors encountered

- SSR 500 (dev server): `Cannot find module './vendor-chunks/lucide-react.js'` in `frontend\.next\server\webpack-runtime.js` requiring `frontend\.next\server\app\analyses\[id]\handover\page.js`. Fix: restart dev server (root cause: `next build` overlapping the running dev server's `.next`).
- Render data endpoints: `OperationalError: no such table: handovers_analysis` (all of list/create/detail/review-summary at test time).
- PowerShell: `Invoke-WebRequest` → "The request was aborted: The connection was closed unexpectedly" intermittently against Render; `curl.exe` succeeded — client quirk.
- Keyless create: HTTP 400 until the payload matched `DEMO_SCENARIO`'s schema.
- Vercel: `npm error code EBADPLATFORM` / `notsup Unsupported platform for @next/swc-win32-x64-msvc@15.5.24 ... linux x64`.
- CDP probe confusion: fetches from an `about:blank` page all failed ("Failed to fetch") because origin `null` is CORS-blocked — resolved by probing from real `localhost:3000` pages.

## Test / build / API results

- Headless Edge (CDP) verification: `/analyses` PASS; `/analyses/2` — review tab loaded, clicked "Final handover" `[role="radio"]` → final view loaded (`Open for receiving clinician`, `Copy handover text`, `Rejected findings are excluded` present; `Finish the review` absent; `Allergy / Adverse reaction`, `HSP-A48291` present); `/analyses/2/handover` PASS (`Handover for receiving clinician`, `Clinically important items to address`, `Print / Save as PDF`, `HSP-A48291`).
- `npm run build` route table: `/` (○), `/_not-found` (○), `/analyses` (○), `/analyses/[id]` (ƒ), `/analyses/[id]/handover` (ƒ), `/workspace` (○) — "Compiled successfully in 20.7s".
- Keyless `:8001` API battery: `GET /api/health/` 200; `GET /api/analyses/` 200 `count=5`; `POST /api/analyses/` (advanced) 201 `{"id":8,"status":"completed"}` with 1 finding (minimal test input); `POST /findings/<id>/review/` decision `accepted`; `GET /api/analyses/8/review-summary/` `{total:1,pending:1}` → `{accepted:1,pending:0}`; `Access-Control-Allow-Origin: *`.
- Deployed: `GET https://medical-handover.onrender.com/api/health/` → 200 at all checks (last check after user's "backend is good").

## Git evidence

- Repo: `https://github.com/ekoechmboya/medical-handover.git`, branch `main`.
- Prior commits: `ce44ae5 database fix`, `cf2a189 Initial Commit`.
- This session: `2ec2ea6 remove win32 swc dep to fix linux/vercel build; untrack tsbuildinfo` — `4 files changed, 3 insertions(+), 4 deletions(-)` (`.gitignore` +1, `frontend/package.json` −1, `frontend/package-lock.json`, deletion of `frontend/tsconfig.tsbuildinfo`).
- `git status` clean at end of session; `HEAD = 2ec2ea6`.
- Secrets check: `git check-ignore -v` confirmed `.env`, `backend\.venv`, `frontend\.next` are ignored; `git ls-files` showed only `frontend/.env.development`/`frontend/.env.example` tracked among env files (both contain the public Render URL, no secrets).

## Important implementation decisions / before→after

- **Before:** frontend default API = `http://127.0.0.1:8000`; deployed Render backend broken (500 no-table); Vercel build failed (EBADPLATFORM). **After:** frontend default = `https://medical-handover.onrender.com`; `render.yaml` self-migrates at boot; keyless operation proven; Vercel build green; commit `2ec2ea6` pushed with clean tree.
- Kept env-var override and SQLite/mock fallbacks — no application-code changes were required for any deployment fix.

## Cross-record observation (not reconciled in this session)

A prior session doc (`docs/sessions/supabase-postgres-migration`) states `settings.py` became Postgres-only (fail loud without `DATABASE_URL`) and that `DATABASE_URL` was added to `.env`. **This session observed the opposite on the very same files**: `settings.py` (at HEAD `ce44ae5`/`2ec2ea6`) contains a SQLite fallback default, and the repo `.env` contained only Gemini variables with no `DATABASE_URL`. The two records disagree; whichever is accurate was not resolvable from this session's evidence alone and is flagged as unverified.