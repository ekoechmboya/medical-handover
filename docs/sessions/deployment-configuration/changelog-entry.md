# Improvement Changelog Entry — deployment-configuration

## Problem or hypothesis

The frontend still pointed at a local Django server while the backend had been deployed to Render (`https://medical-handover.onrender.com`). Hypothesis (confirmed): the deployed service was misconfigured — no environment variables, SQLite fallback active, and migrations never run — so every data endpoint returned HTTP 500 `OperationalError: no such table: handovers_analysis` even though `/api/health/` was green. Separately, the frontend's Vercel (linux) build failed on `npx install` with `EBADPLATFORM` because a session-pinned, Windows-only SWC package was a direct dependency.

## What was tried

1. Tested the deployed backend (health 200; data endpoints 500) and read the public Django DEBUG page to prove env/migration state.
2. Switched the frontend default API base URL to the deployed backend (code default + `.env.development`/`.env.example`).
3. Changed `render.yaml` so `startCommand` runs `python manage.py migrate --noinput` at every boot.
4. Proved the backend runs with zero keys via a local "keyless" simulation (hidden `.env`, cleared env vars, second instance on `:8001`).
5. Supplied the exact Render environment variable set (Gemini key from repo `.env`, `MH_EMITTER_BACKEND=gemini`, model, generated Django secret, `DJANGO_DEBUG=0`, plus required `DATABASE_URL` format).
6. Removed `@next/swc-win32-x64-msvc` from `frontend/package.json` and regenerated the lockfile.
7. Committed and pushed to GitHub so the hosting pipelines rebuild from `main`.

## Why this approach was chosen

- Keeping the env-var override (`NEXT_PUBLIC_API_BASE_URL`) means the same code can target local or deployed backends; production builds naturally fall back to the code default.
- Migrating at boot removes the fragile dependency on `postDeployCommand` (which never runs on a manually-created Render service) and on the deployed instance's ephemeral filesystem state.
- Keyless simulation isolates deploy configuration from the application: the app's defaults (SQLite fallback + mock emitter) are proven sufficient for an offline demo.
- Removing the platform pin (rather than adding per-platform pins) lets npm resolve Next.js's own per-platform optional SWC dependencies on any CI host.

## What happened

- Root-caused and cleared the dev-server `.next` corruption left by an earlier `next build` (the `/analyses/[id]/handover` SSR 500 masking API health).
- Confirmed the deployed frontend now requests `https://medical-handover.onrender.com` (health "API online"; list surfaces the backend's 500 in the error UI).
- Verified the backend works end-to-end with no keys: health 200, list 200, create 201 (`id=8`, completed), accept review → `review-summary {accepted:1, pending:0}`, CORS `*`.
- Frontend `typecheck`/`lint`/`next build` all green on 6 routes after the SWC fix.
- Pushed to GitHub (`2ec2ea6`), leaving the tree clean so Vercel/Render can auto-deploy.

## Evidence or validation

- Deploy endpoint 500 debug page: `Django Version: 6.1`, `Exception Value: no such table: handovers_analysis`, SQLite `DatabaseWrapper`, `DEBUG=True`, `MIDDLEWARE [config.middleware.DemoCORSMiddleware]`, `EMITTER_BACKEND 'mock'`.
- Keyless simulation API battery on `127.0.0.1:8001` (details above) — all pass.
- `pip install -r requirements.txt` → `Successfully installed dj-database-url-2.3.0 gunicorn-23.0.0 psycopg-3.3.4 psycopg-binary-3.3.4`.
- Vercel log: `npm error notsup Unsupported platform for @next/swc-win32-x64-msvc@15.5.24: wanted {"os":"win32","cpu":"x64"} (current: {"os":"linux","cpu":"x64"})`.
- `git push` → `ce44ae5..2ec2ea6  main -> main`; `git status` clean.

## Decision or next step

Standardize the deployment contract: `render.yaml` migrates at boot; the frontend defaults to the deployed backend; the deployed service should carry `DJANGO_DEBUG=0`, the Gemini key/emitter/model, a generated secret, and a real `DATABASE_URL` (Postgres) once durable storage is wanted. Next step: confirm the GitHub-triggered Vercel build and Render redeploy are green after commit `2ec2ea6`, and re-run the full API contract (list/create/review/final-handover) against the deployed Render endpoint.