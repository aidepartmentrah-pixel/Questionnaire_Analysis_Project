# Deployment

The live demo runs on [Render](https://render.com) as **two independent Docker
web services** — one for the backend, one for the frontend — rather than
`docker compose`, since Render builds and runs one Dockerfile per service, not
a compose file. This doc covers how it's configured, the mistakes that ate the
most time getting it right, and how to manage it day to day.

## Live services

| Service | Role | URL |
|---|---|---|
| `questionnaire-analysis-project-3` | Backend (FastAPI) | https://questionnaire-analysis-project-3.onrender.com |
| `questionnaire-analysis-frontend` | Frontend (static React build, served by nginx) | **https://questionnaire-analysis-frontend.onrender.com** ← the app |

Both run on Render's free plan, region Ohio (US East). Free instances spin
down after ~15 minutes idle; the next request wakes them back up in 30-60s.
That's normal, not a bug — don't panic if the first load of a demo session is
slow.

> The backend's service name ended up as `questionnaire-analysis-project-3`
> rather than something cleaner, as a side effect of the trial-and-error
> below (several earlier attempts were misconfigured and abandoned rather
> than renamed). Functionally it doesn't matter — it's just the URL.

## How the two services connect

This is the part that isn't obvious and caused every real issue during setup:

1. The **frontend is a static build** — Vite compiles the React app into
   plain HTML/CSS/JS once, at *build time*, and nginx just serves those files
   afterward. There is no Node server running, and nothing is read from the
   environment at runtime.
2. Because of that, the backend's URL has to be **baked into the JavaScript
   at build time** via `VITE_API_BASE_URL` (Vite inlines any `VITE_*`
   variable directly into the compiled bundle). The frontend's `Dockerfile`
   declares `ARG VITE_API_BASE_URL` before running `npm run build` — Render
   forwards a same-named Environment Variable on the service through to the
   Docker build as that build-arg, but **only if the variable is actually
   set before the build runs**.
3. Once both services are live, the **browser talks directly to the
   backend** — not through nginx as a proxy. That means the backend's CORS
   setting must explicitly allow the frontend's origin, or the browser
   blocks every request with no useful error beyond "network error."

```
Browser ──(loads static files)──► frontend (nginx)
Browser ──(API calls, cross-origin)──► backend (FastAPI, must allow this origin via CORS)
```

## Exact configuration

Both services are **Docker** runtime, source = this repo, branch `main`.

### Backend (`questionnaire-analysis-project-3`)

| Field | Value |
|---|---|
| Dockerfile Path | `backend/Dockerfile` |
| Docker Build Context Directory | `backend` |
| Docker Command | *(blank — let the Dockerfile's own `CMD` run)* |
| Health Check Path | `/api/health` |

Environment variables:
```
APP_ENVIRONMENT   = production
APP_CORS_ORIGINS  = ["https://questionnaire-analysis-frontend.onrender.com"]
```
`APP_CORS_ORIGINS` must be valid JSON (square brackets, double quotes) — the
setting is parsed as a JSON array, not a comma-separated string.

### Frontend (`questionnaire-analysis-frontend`)

| Field | Value |
|---|---|
| Dockerfile Path | `frontend/Dockerfile` |
| Docker Build Context Directory | `frontend` |
| Docker Command | *(blank)* |
| Health Check Path | `/` |

Environment variables:
```
VITE_API_BASE_URL = https://questionnaire-analysis-project-3.onrender.com
```

Both fields — **Dockerfile Path** and **Docker Build Context Directory** —
are relative to the *repository root*, not to each other. This is a monorepo
with the Dockerfile living inside a subdirectory, so both need the full path
(`backend/Dockerfile` + `backend`), not just the filename with an implied
directory.

## Gotchas actually hit getting here

Documented because each one produced a confusing symptom with a non-obvious
cause — worth knowing if this ever needs rebuilding from scratch.

1. **Build Context Directory left at the default (`.`, repo root) while only
   Dockerfile Path was set.** The Dockerfile loaded fine, but `COPY app
   ./app` failed with `"/app": not found` — because with context = repo
   root, that `COPY` looks for a top-level `app/` folder, which doesn't
   exist (it's at `backend/app/`). Both fields need to point at the
   subdirectory, not just one of them.
2. **A value accidentally landed in "Docker Command"** (which overrides the
   container's `CMD`/`ENTRYPOINT`) instead of "Docker Build Context
   Directory" — two visually similar fields, easy to fill in the wrong one.
   Left blank, the Dockerfile's own `CMD` (`uvicorn ...`) runs correctly.
3. **`VITE_API_BASE_URL` was never added at all on the first frontend
   deploy.** The build silently fell back to the Dockerfile's default
   (`http://localhost:8000`), which got compiled into the shipped JS. Every
   visitor's browser then tried to reach `localhost:8000` — on an HTTPS
   page, that's a mixed-content request browsers block outright, so it
   surfaced as a generic "Backend unreachable" / "Network error" with no
   direct clue. **How this was actually confirmed** (build logs don't show
   it): fetch the deployed JS bundle and grep it for the literal API URL
   string —
   ```bash
   JS_FILE=$(curl -s https://<frontend-url>/ | grep -o 'assets/index-[^"]*\.js')
   curl -s "https://<frontend-url>/$JS_FILE" | grep -o 'https\?://[a-zA-Z0-9.-]*onrender\.com'
   ```
   If that prints `localhost` instead of the real backend URL, the env var
   didn't reach the build — add/fix it and trigger a fresh deploy.
4. **CORS blocks requests even when both URLs are correct**, if the
   backend's `APP_CORS_ORIGINS` doesn't list the frontend's exact origin.
   This is a runtime setting (read per-request), so fixing it only needs a
   restart, not a rebuild — much faster to iterate on than the build-arg
   issue above.
5. **Health Check Path defaults to Render's placeholder `/healthz`**, which
   doesn't exist in this app. Left unset, Render will flag an otherwise-fine
   service as unhealthy. Set explicitly per service (see table above).
6. **Several broken services accumulated from retrying via "create a new
   service" instead of fixing the existing one's Settings tab** — each
   partial misconfiguration got a new service rather than a fix in place.
   If cleaning up: only `questionnaire-analysis-project-3` (backend) and
   `questionnaire-analysis-frontend` are real; anything else with a similar
   name is a leftover and safe to delete.

## Managing the deployment

### Dashboard

https://dashboard.render.com — each service has **Environment** (env vars,
separate tab from Settings), **Settings** (Dockerfile path, build context,
health check, etc.), **Logs**, and **Events** (deploy history). Changing an
Environment Variable or a Settings field auto-triggers a redeploy.

### Render CLI

Faster for checking status, watching a build, or forcing a redeploy without
clicking through the dashboard.

**Install (Windows):** download the `windows_amd64` asset from the
[Render CLI releases page](https://github.com/render-oss/cli/releases) —
not `darwin` (macOS) or `linux`. Unzip it and run `render.exe` directly, or
put it on your `PATH`.

```bash
render login                              # opens a browser to authorize
render workspace set <workspace-id>       # once, after first login
render services                           # list every service + full config
render deploys create <service-id> --wait # trigger a redeploy, wait for it to finish
render logs <service-id>                  # tail runtime logs
render restart <service-id>               # restart without rebuilding
```

`render services --output json` is the fastest way to double-check a
service's *actual* configured values (Dockerfile path, build context,
health check, etc.) when something's not working as expected — faster than
navigating the dashboard, and it's what caught gotcha #1 and #2 above.

**What the CLI can't do:** manage Environment Variables, and deleting a
service requires an explicit interactive confirmation — both are
dashboard-only operations as of CLI v2.28.0.

## Redeploying after a code change

Auto-deploy is on for both services (`On Commit`, branch `main`) — pushing to
`main` redeploys whatever changed. To force a redeploy without a new commit
(e.g. after only changing an Environment Variable, which usually
auto-triggers one anyway): `render deploys create <service-id> --wait`.
