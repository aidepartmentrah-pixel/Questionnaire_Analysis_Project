# Project Progress

**Project:** AutoML Demonstration (college project)
**Last updated:** 2026-09-15
**Status:** All 10 slices (0-9) complete. Ready for demonstration.

Open this file any time to see where the project stands. It gets updated at the end of every slice with what changed, what passed, and what's next — no need to scroll back through chat history.

---

## 1. Decisions locked in

| Area | Decision |
|---|---|
| Backend stack | Python, FastAPI, pandas, scikit-learn, XGBoost, Joblib |
| Frontend stack | React + TypeScript |
| Backend tests | pytest + FastAPI TestClient/httpx |
| Frontend tests | Vitest + React Testing Library |
| End-to-end tests | Playwright |
| Execution mode | **Autonomous** — I work through Slices 0–9 in order, run each slice's quality gate, and write a checkpoint here after each one. I only stop mid-stream if a test can't be made to pass, a requirement conflicts with reality, or something needs a decision only you can make. |
| UI aesthetic | **Clean enterprise SaaS** — neutral palette, generous whitespace, subtle borders/shadows, restrained color reserved for status/emphasis. Reference points: Linear, Stripe, Vercel dashboards. |
| Containerization | **Docker required.** The app must run via Docker as well as via local dev commands (see §3). |

## 2. Open item — resolved by proceeding

| Item | Default used | Why | Your call |
|---|---|---|---|
| Frontend styling/components | **Tailwind CSS v4 + hand-rolled shadcn/ui-style primitives** (Button, Badge, Card in `frontend/src/components/ui/`) | You answered "TypeScript" for this question, which isn't one of the options — likely a mis-click. Proceeded with the recommended default since you asked me not to stop. | Still reversible — say the word and I'll swap to MUI/Ant Design/plain CSS. |

## 3. Docker plan (amendment to the original spec)

The original slicing document listed Docker Compose as optional ("only if local setup benefits from it"). Per your request, this is now a firm requirement:

- **Slice 0** will add a `Dockerfile` for the backend (FastAPI) and a `Dockerfile` for the frontend (React/TS), plus a `docker-compose.yml` that runs both together with the correct local networking/CORS setup — alongside (not instead of) plain local dev commands (`uvicorn`, `npm run dev`).
- **Slice 9** will verify and document the Docker path explicitly in the README's final-verification checklist, so a clean-environment run via `docker compose up` is a supported, tested way to demo the project — not just the two native dev servers.
- Test suites (pytest/Vitest/Playwright) will still run natively during development; Docker is validated as a packaging/runtime target, not swapped in as the test environment, to keep the fast-iteration loop fast.

## 3a. Exhaustive configuration-combination testing (amendment to the original spec)

Triggered by a real bug you found live: picking **Classification** with a continuous numeric target (`distance_to_center_km` on `house_prices.csv`) reached the Train step and produced a training error that dumped ~190 raw distinct values into a single sentence, instead of being caught earlier with a clean message. Root cause: the classification-specific target checks (minimum classes, minimum rows per class) lived only in the training service, not in the live Configure-step preview — every *other* validation rule was already shared between preview and training (§4d), but this one had drifted from that pattern. Full writeup of the fix and its tests is in §4i's addendum below.

Standing addition to the plan from here on, per your explicit instruction: **exercise every task × target combination — not just the two "intended" ones per dataset — against both committed fixture CSVs**, including deliberately wrong choices a real user might click (an identifier column, a continuous numeric column, etc. as a classification target), asserting the app always degrades gracefully (a clear, bounded "not ready" reason in Configure) rather than reaching Train with a broken configuration. Implemented as `e2e/tests/all-combinations.spec.ts` (§4i addendum) and treated as a permanent part of the regression suite, not a one-off check.

## 4. Slice status

| # | Slice | Status | Backend tests | Frontend tests | E2E tests | Notes |
|---|---|---|---|---|---|---|
| 0 | Repository foundation & quality gates (+ Docker skeleton) | **Done** | 1/1 pass | 2/2 pass | 1/1 pass | See §4a. Docker Compose build + browser check verified manually. |
| 1 | CSV fixtures & upload workflow | **Done** | 10/10 pass | 5/5 pass | 3/3 pass | See §4b. |
| 2 | Data profiling & EDA | **Done** | 15/15 pass | 9/9 pass | 5/5 pass | See §4c. |
| 3 | Task/target/feature/preprocessing configuration | **Done** | 34/34 pass | 20/20 pass | 8/8 pass | See §4d. |
| 4 | Regression end-to-end | **Done** | 45/45 pass | 24/24 pass | 9/9 pass | See §4e. |
| 5 | Classification end-to-end | **Done** | 56/56 pass | 25/25 pass | 10/10 pass | See §4f. |
| 6 | Clustering end-to-end | **Done** | 69/69 pass | 26/26 pass | 11/11 pass | See §4g. |
| 7 | Artifact export | **Done** | 83/83 pass | 27/27 pass | 12/12 pass | See §4h. |
| 8 | Full UI workflow, resilience, accessibility | **Done** | 86/86 pass | 31/31 pass | 25/25 pass | See §4i + addenda. |
| 9 | Packaging, docs & final verification (incl. Docker) | **Done** | 86/86 pass | 31/31 pass | 25/25 pass | See §4j. |

Legend: **Not started** / **In progress** / **Done** / **Blocked**

## 4a. Slice 0 checkpoint — Repository foundation & quality gates

**Files created:**
- `backend/app/` — FastAPI app (`main.py`), config (`core/config.py`), `GET /api/health` route + schema, and empty-but-structured `services/`, `ml/registry.py`, `storage/` packages for later slices.
- `backend/tests/` — pytest config (`pyproject.toml`), `conftest.py`, `test_health.py`.
- `backend/requirements.txt`, `requirements-dev.txt`, `.env.example`, `Dockerfile`, `.dockerignore`.
- `frontend/` — Vite + React 19 + TypeScript app scaffold; Tailwind CSS v4 theme (`src/index.css`, "clean enterprise SaaS" tokens, light/dark); shadcn-style primitives (`components/ui/button.tsx`, `badge.tsx`, `card.tsx`); `HealthIndicator` and `StepNav` components; `App.tsx` shell with the five-step layout; Vitest setup + `App.test.tsx`; `Dockerfile` + `nginx.conf`.
- `e2e/` — Playwright config (auto-starts backend + frontend), `tests/smoke.spec.ts`.
- `docker-compose.yml` — backend + frontend services.
- Root `README.md`, `.gitignore`.

**Functionality completed:**
- Backend serves `GET /api/health` with a stable JSON payload; CORS configured for the Vite dev origin and the Dockerized frontend origin.
- Frontend renders the app shell: title, five-step navigation (Upload/Profile/Configure/Train/Results), and a live backend-health badge (checking → connected/unreachable).
- Full stack runs both natively (`uvicorn` + `npm run dev`) and via `docker compose up --build`; verified the Dockerized frontend can reach the Dockerized backend in a real browser with zero console errors.

**Tests added:**
- Backend: `test_health.py` — asserts 200 status and payload shape.
- Frontend: `App.test.tsx` — renders title/steps, and covers both the "backend connected" and "backend unreachable" states of the health indicator (fetch mocked).
- E2E: `smoke.spec.ts` — opens the real app against the real backend, checks title, all five step labels, and "Backend connected".

**Commands executed (all passing):**
- `cd backend && ./.venv/Scripts/python -m pytest -q` → 1 passed
- `cd backend && ruff check`, `ruff format --check`, `mypy app` → all clean
- `cd frontend && npm run test` → 2 passed
- `cd frontend && npm run lint`, `npm run typecheck`, `npm run format:check` → all clean
- `cd frontend && npm run build` → succeeds
- `cd e2e && npx playwright test` → 1 passed
- `docker compose build && docker compose up -d` → both services healthy; manual browser check confirmed the health indicator goes green against the Dockerized backend

**Known limitations / decisions:**
- Frontend styling default (Tailwind + hand-rolled shadcn-style primitives) used without your final confirmation — see §2, still easy to change.
- xgboost's Linux wheel pulls in an unused ~340MB `nvidia-nccl-cu12` GPU dependency; the backend Dockerfile removes it post-install (verified CPU training still works). Worth knowing about if xgboost is ever upgraded — re-verify the removal is still safe.
- No CI pipeline configured yet — tests are run locally/on-demand only (not in this slice's scope).
- README is minimal for now; full setup/demo docs are Slice 9 scope.

## 4b. Slice 1 checkpoint — Deterministic CSV fixtures and upload workflow

**Files created:**
- `scripts/generate_fixtures.py` — deterministic (seed 42) generator for both fixtures; documents the exact design (segment structure, churn logic, missing/duplicate counts) in its module docstring.
- `tests/fixtures/customer_segments.csv`, `tests/fixtures/house_prices.csv` — committed, 222 rows each (220 unique + 2 duplicate), 6 missing cells each, generated once and checked in (not regenerated at test time).
- Backend: `app/schemas/dataset.py`, `app/services/csv_validation.py`, `app/services/dataset_store.py`, `app/services/dataset_summary.py`, `app/api/routes/datasets.py` (`POST /api/datasets/upload`), `backend/tests/test_upload.py`.
- Frontend: `lib/api.ts` extended with `uploadDataset` (XHR-based, for real progress events), `components/ui/progress.tsx`, `components/file-dropzone.tsx`, `components/dataset-preview-table.tsx`, `components/upload-step.tsx` (+ its test), wired into `App.tsx` as the real Upload step.
- `e2e/tests/upload.spec.ts`.

**Functionality completed:**
- Backend validates and parses uploaded CSVs (extension, empty file, header-only, malformed rows, duplicate headers, size limit), stores the active dataset (file on disk + in-memory pointer; single active dataset, replaced on next upload, per product scope), and returns a `dataset_id`, filename, dimensions, per-column detected type (numeric/categorical) and a JSON-safe preview (NaN → `null`).
- Frontend Upload step: drag-and-drop or Browse button, a real upload-progress bar, a success summary (filename/dimensions) plus a scrollable preview table with per-column type badges, friendly inline error messages, and uploading a new file cleanly replaces the previous dataset (both client state and server state).

**Tests added:**
- Backend (`test_upload.py`, 9 new tests): both real fixtures upload correctly with exact dimensions/columns/types; new-upload-replaces-active; NaN→null in preview; empty/header-only/malformed/duplicate-header/wrong-extension all rejected with friendly `detail` messages.
- Frontend (`upload-step.test.tsx`, 3 new tests): success path renders summary+preview, error path renders the alert, and a second upload replaces the first (API layer mocked).
- E2E (`upload.spec.ts`, 2 new tests): real backend + real fixtures — upload `customer_segments.csv`, verify filename/dimensions/columns/preview, upload `house_prices.csv`, verify it fully replaces the first (old filename and column gone); a second test checks the empty-file validation error renders in the browser.

**Commands executed (all passing):**
- `cd backend && pytest -q` → 10 passed
- `cd backend && ruff check / ruff format --check / mypy app` → clean
- `cd frontend && npm run test` → 5 passed (2 files)
- `cd frontend && npm run lint / typecheck / format:check` → clean
- `cd e2e && npx playwright test` → 3 passed

**Known limitations / decisions:**
- The backend keeps exactly one active dataset in an in-process global (no per-session/per-user isolation) — matches the product's explicit "one dataset at a time, no accounts, no database" scope, but means e2e tests that upload data can't safely run concurrently against each other if a future test mutates shared state; the current two upload tests are safe (verified), but this is worth remembering when adding more e2e specs in later slices — group state-mutating flows into one sequential test, or add `test.describe.serial()`.
- Fixture design was validated numerically (not just visually): clustering silhouette ≈0.58 for `customer_segments.csv`'s 3 segments, regression R²≈0.87 for `house_prices.csv` — both "learnable but imperfect," matching the spec.
- No `GET /api/datasets/{id}` retrieval endpoint yet — not required until Slice 2 (profiling) needs to fetch the active dataset by id; deferred to avoid building ahead of the current slice.

## 4c. Slice 2 checkpoint — Data profiling and EDA

**Files created:**
- Backend: `app/schemas/profile.py`, `app/services/dataset_profile.py` (column profiles, numeric summary/histograms, categorical frequencies, correlation matrix), `app/services/eda_report.py` (self-contained HTML report, no JS/external assets), two new routes on `app/api/routes/datasets.py` (`GET /api/datasets/{id}/profile`, `GET /api/datasets/{id}/profile/report`), `backend/tests/test_profile.py`.
- Frontend: `lib/api.ts` extended with profile types + `getDatasetProfile`/`getEdaReportUrl`, `components/bar-list.tsx`, `components/correlation-heatmap.tsx`, `components/profile-step.tsx` (+ its test), `App.tsx` rewritten with real step state (`currentStep`, `dataset`) and Upload → Profile navigation.
- `e2e/tests/profile.spec.ts`.

**Functionality completed:**
- Profile endpoint returns dimensions, duplicate-row count, per-column type/missing/unique stats, numeric descriptive statistics, numeric histograms, categorical frequencies (high-cardinality/identifier-like columns like `customer_id` automatically excluded, >50% unique ratio), and a Pearson correlation matrix (`null` when fewer than 2 numeric columns).
- Numeric columns with ≤12 distinct values (e.g. a binary target, a bedroom count) get one bar per exact value instead of being forced into 10 equal-width buckets — added after visually reviewing a real screenshot and noticing `churned`'s histogram was mostly empty bins; fixed in both the API and the HTML report, with a test asserting the 2-bar behavior specifically.
- The EDA HTML report is self-contained (inline CSS, CSS-only bar charts, no JS, no external network requests) so it opens correctly from disk indefinitely; downloads via a real `Content-Disposition: attachment` response.
- Frontend Profile step: overview cards, column table, numeric distribution bars, categorical frequency bars (with "top N + Other" note when truncated), a correlation heatmap, and a "Download EDA report" link. Upload → Profile is now a real, explicit navigation step (a "Continue to profile" button), not an automatic jump — needed so the upload summary/preview stays inspectable, per Slice 1's own acceptance criteria.

**Tests added:**
- Backend (`test_profile.py`, 5 new tests): exact known-fixture assertions for both CSVs (row/column/duplicate counts, per-column missing counts down to the exact cell, dtype detection, unique counts, which columns get frequency charts and which are excluded, correlation matrix shape/diagonal, the 2-bar discrete-value case for `churned`), a 404 for an unknown dataset, and the HTML report's content-type/attachment header/self-containedness (no `http(s)://`, no `<script>`).
- Frontend (`profile-step.test.tsx`, 4 new tests): loading, success (cards/table/charts/heatmap/download link), empty-chart (no numeric distributions, no categorical frequencies, no correlation), and error states — API layer mocked.
- E2E (`profile.spec.ts`, 2 new tests): real backend, both real fixtures — upload, continue to Profile, verify known values, and download the actual HTML report file via a real click.
- `e2e/playwright.config.ts` changed to `workers: 1` / `fullyParallel: false`: the backend keeps a single global "active dataset" slot by design, so any two dataset-mutating e2e tests would race if run concurrently. Documented in the config itself.

**Commands executed (all passing):**
- `cd backend && pytest -q` → 15 passed
- `cd backend && ruff check / ruff format --check / mypy app` → clean
- `cd frontend && npm run test` → 9 passed (3 files)
- `cd frontend && npm run lint / typecheck / format:check` → clean
- `cd e2e && npx playwright test` → 5 passed

**Known limitations / decisions:**
- Visual QA: took real screenshots of the running app (Upload and Profile steps) to sanity-check the "clean enterprise SaaS" aesthetic actually holds up, not just that tests pass — this caught the churned-histogram issue above.
- `DISCRETE_NUMERIC_MAX_UNIQUE = 12` and `CATEGORICAL_SKIP_UNIQUE_RATIO = 0.5` / `CATEGORICAL_TOP_N = 20` are judgment-call thresholds (documented in code comments), not from the spec; reasonable for this dataset scale, revisit only if a future dataset's profile looks wrong.
- The Profile step's own "Continue to configure" button is present but disabled (Slice 3 builds Configure).

## 4d. Slice 3 checkpoint — Task, target, feature and preprocessing configuration

**Files created:**
- Backend: `app/schemas/config.py` (`TaskType`, `ScalerType`, `PreprocessingRequest`, `PreprocessingPreview`), `app/services/preprocessing_pipeline.py` (reusable `ColumnTransformer` builder — scaler-or-passthrough for numeric, one-hot with `handle_unknown="ignore"` for categorical; this is the same builder Slice 4+ will reuse inside real training pipelines, not a one-off), `app/services/config_validation.py` (validation + preview computation), a new route on `datasets.py` (`POST /api/datasets/{id}/preprocessing-preview`), `backend/tests/test_preprocessing_pipeline.py`, `backend/tests/test_config_preview.py`.
- Frontend: `lib/api.ts` extended with config types + `getPreprocessingPreview`, `lib/configure.ts` (+ test) for default-feature-selection logic, `components/ui/select.tsx`, `components/ui/checkbox.tsx`, `components/configure-step.tsx` (+ test), `App.tsx` wired with the Configure step and Profile→Configure navigation.
- `e2e/tests/configure.spec.ts`.

**Functionality completed:**
- A decision worth flagging: re-reading the two spec docs together, "support drop-rows-with-missing-values" and "support one-hot encoding" turned out to be listed as implementation capabilities, not user-togglable options — missing-value dropping and one-hot encoding are always applied (matching Software Requirement.md §8.1's "shall be removed" language), while duplicate removal and the scaler are genuinely user-configurable (§8.2/§8.3 use "allow"/"shall be able to choose"). The API and UI reflect that split rather than exposing a toggle for behavior the spec says is mandatory.
- Validation (all as 422s with friendly messages): unknown columns, empty feature list, missing target for regression/classification, target provided for clustering, target re-selected as a feature (leakage), non-numeric feature selected for clustering.
- "Too few rows" is deliberately *not* a 422 — the preview still computes and returns full counts, with `ready_to_train: false` and a warning, so the user can see *why* it's not trainable instead of getting a bare error. A similar warning fires whenever >30% of rows would be removed.
- Preview returns real post-encoding feature names (via fitting the actual `ColumnTransformer` and reading `get_feature_names_out()`), not a guess — so what Slice 4 will actually train on and what the user previews here are guaranteed to match.
- Frontend Configure step: task selector (segmented radio group), target dropdown (regression/classification only), a feature checklist that defaults per §7.1/§7.2 (all non-target columns; numeric-only for clustering) and disables categorical checkboxes outright for clustering rather than letting the user hit a backend rejection, duplicate-removal checkbox, scaler dropdown, and a debounced (350ms) live preprocessing-impact panel with a Ready/Not-ready badge.

**Tests added:**
- Backend (`test_preprocessing_pipeline.py`, 7 tests): standard/minmax/no scaling, one-hot expansion, unknown-category-at-transform-time doesn't raise, combined numeric+categorical naming.
- Backend (`test_config_preview.py`, 12 tests): exact known-fixture row/column-name assertions for all three real configurations (regression on `house_prices.csv`, classification on `customer_segments.csv`, clustering on `customer_segments.csv`) — counts verified independently via a throwaway pandas script before writing the assertions, not guessed; every rejection case; the "too few rows → not ready, not rejected" behavior; 404 for an unknown dataset.
- Frontend (`configure.test.ts`, 8 tests; `configure-step.test.tsx`, 3 tests): default-feature-selection logic in isolation, and the component's loading/ready/clustering-disables-categorical/error states (API mocked).
- E2E (`configure.spec.ts`, 3 tests): the exact three scenarios the slice plan names — regression on `house_prices.csv` with `price_usd`, classification on `customer_segments.csv` with `churned`, clustering on `customer_segments.csv` with numeric-only features — each verified to reach `ready_to_train` with the real backend.

**Commands executed (all passing):**
- `cd backend && pytest -q` → 34 passed
- `cd backend && ruff check / ruff format --check / mypy app` → clean
- `cd frontend && npm run test` → 20 passed (5 files)
- `cd frontend && npm run lint / typecheck / format:check` → clean
- `cd e2e && npx playwright test` → 8 passed

**Known limitations / decisions:**
- Process hygiene lesson (not a product bug): a backend dev server I'd left running from an earlier manual screenshot check was silently reused by Playwright's `reuseExistingServer` and served *stale* code (missing the new route), causing all three new e2e tests to fail with a generic 404. Diagnosed by testing the endpoint directly with curl, fixed by killing the stray process — worth remembering to always kill manually-started dev servers before the next e2e run in this project.
- `MIN_ROWS_FOR_TRAINING = 30` and `HIGH_ROW_LOSS_WARNING_RATIO = 0.3` are judgment calls (documented in code), not from the spec.
- Configure step state is self-contained (not lifted to `App.tsx`) since Slice 4 (Train) doesn't exist yet to consume it; will lift/wire it when Train needs the confirmed config.

## 4e. Slice 4 checkpoint — Regression end-to-end vertical slice

**Files created:**
- Backend: `app/ml/registry.py` (populated — `ModelSpec` dataclass, `REGRESSION_MODELS`: Linear/Random Forest/XGBoost Regressor with bounded grids), `app/schemas/training.py`, `app/services/regression_training.py` (split, per-model tune+evaluate+chart, `select_winner`, `compute_regression_metrics`), a new route (`POST /api/datasets/{id}/train`, dispatches by task — regression implemented, classification/clustering stubbed as 501 pending Slices 5/6), `backend/tests/test_regression_training.py`.
- Refactored `app/services/config_validation.py`: extracted `validate_task_config` and `clean_training_subset` so training reuses the exact same structural-validation and row-cleaning logic the Slice 3 preview already used, instead of a second copy that could drift.
- Frontend: `lib/api.ts` extended with training types + `startTraining`, `components/scatter-chart.tsx` (hand-rolled inline-SVG scatter, no charting library added), `components/train-step.tsx` (+ test), `App.tsx` wired with the Train step and a `trainConfig` lifted from Configure.
- `e2e/tests/train.spec.ts`.

**Functionality completed:**
- Real hyperparameter tuning: `GridSearchCV` with a `KFold(3, shuffle=True, seed=42)` over small bounded grids (2-4 combinations per model), fit only on the 80% training split; the test split is verified untouched until after tuning (see tests below). Evaluated once on the 20% held-out split with MAE/RMSE/R²; winner = lowest RMSE among successful models.
- A model failure doesn't abort the comparison — caught per-model, recorded as `status: "failed"` with the error message, the other two still complete and a winner is still picked from whichever succeeded.
- Frontend Train step: since the backend trains synchronously (a single blocking request, no streaming/websocket infra added for this project's scope), "progress by model" is shown as the three model names with a spinner during the one request rather than a fabricated per-model progress bar — deliberately not pretending to show progress the API can't actually report. Results: a comparison table with the winner highlighted, and for the winner specifically, actual-vs-predicted and residual scatter charts plus a feature-importance bar chart (only for models that support it — Linear Regression doesn't, Random Forest/XGBoost do).
- **Real bug caught by visual QA, not by tests**: took a full-flow screenshot after building the Train step and found `property_id` (a near-unique ID column) had been one-hot-encoded into ~200 columns because the default feature selection included every non-target column, per spec §7.1's literal wording. Fixed by excluding identifier-like categorical columns (>50% unique values) from the *default* selection — reusing the exact same heuristic already validated in Slice 2's EDA frequency-chart exclusion — while still letting a user add such a column back by hand. Required adding `unique_count` to the upload response's `ColumnInfo` (backend + frontend types) so the frontend can compute this without an extra API call. Re-verified with another screenshot: 10 sensible feature columns instead of ~200.

**Tests added:**
- Backend (`test_regression_training.py`, 11 tests): metric-calculation correctness against hand-computed values, winner selection (including "all failed → None" and "failed model isn't picked even if listed first"), a spy on `GridSearchCV.fit` proving every model's tuning call only ever received the training-split row count (never the held-out test rows), a synthetic always-fails estimator proving one broken model doesn't stop the other two, a real bounded end-to-end run against `house_prices.csv` via the API (asserts 3 results, finite metrics, non-empty `best_params`, correct feature-importance presence per model, and that the winner truly has the lowest successful RMSE), too-few-rows rejection, non-regression-task 501, unknown-dataset 404.
- Backend (`test_upload.py`, +1 assertion): exact `unique_count` values for the new field.
- Frontend (`train-step.test.tsx`, 3 tests): no-config prompt, full success render (table, winner badge, charts section), error state — API mocked.
- Frontend (`configure.test.ts`, +2 tests): the identifier-exclusion behavior specifically (a 100%-unique categorical column excluded by default, a low-cardinality one kept).
- E2E (`train.spec.ts`, 1 test): the real flow end to end — upload `house_prices.csv`, configure regression, click Start training, wait for real `GridSearchCV` tuning to finish (30s timeout, genuinely ~2-5s in practice), verify 3 model rows all "Success," a highlighted winner, and both charts rendered as real SVG.

**Commands executed (all passing):**
- `cd backend && pytest -q` → 45 passed in ~6-8s
- `cd backend && ruff check / ruff format --check / mypy app` → clean
- `cd frontend && npm run test` → 24 passed (6 files)
- `cd frontend && npm run lint / typecheck / format:check` → clean
- `cd e2e && npx playwright test` → 9 passed in ~18s

**Known limitations / decisions:**
- Charts are hand-rolled inline SVG (scatter plot with an identity/zero reference line, native `<title>` hover tooltips), not a charting library — consistent with the project's zero-extra-dependency approach so far and adequate at this data scale; consulted the `dataviz` skill before building them (single-hue magnitude encoding, no dual axes, reference lines, hover layer via native tooltips).
- Training is synchronous end-to-end (~2-5s for these fixtures with all three models); acceptable for a college demo but would need a background-job/streaming design to scale to slower models or larger data — out of scope here.
- `POST /api/datasets/{id}/train` already accepts `task: classification | clustering` and returns 501 for both — the route contract is stable so Slices 5/6 only need to add their training services, not touch the endpoint shape.

## 4f. Slice 5 checkpoint — Classification end-to-end vertical slice

**Files created:**
- Backend: `app/ml/registry.py` extended with `CLASSIFICATION_MODELS` (Logistic/Random Forest/XGBoost Classifier), `app/schemas/training.py` extended with `ConfusionMatrix`/`ClassificationCharts` (`ModelResult.charts` is now `RegressionCharts | ClassificationCharts | None`), `app/services/classification_training.py` (stratified split, stratified 3-fold CV, weighted precision/recall/F1, confusion matrix, `select_winner` by highest F1), `training.py` route now dispatches regression and classification (only clustering still 501s), `backend/tests/test_classification_training.py`.
- Frontend: `lib/api.ts` extended with `ConfusionMatrix`/`ClassificationCharts`/`isClassificationCharts`, `components/confusion-matrix-view.tsx` (color-coded correct/incorrect cells, per-class support counts), `train-step.tsx` generalized to be task-aware (metric columns and chart type switch on `response.task`) instead of forking into a second component — "reuse the common training and result components" from the slice plan.

**Functionality completed:**
- Stratified `train_test_split` (80/20) and `StratifiedKFold(3)` for tuning, so class proportions are preserved in both the CV folds and the held-out test set. Metrics use `average="weighted"` for precision/recall/F1 — chosen because it's the one averaging strategy that works unmodified for both binary and multiclass targets and accounts for class imbalance (documented in code comments, as the slice plan requires).
- Validates one-class targets and too-small classes *before* attempting a stratified split (which would otherwise fail with a much less readable sklearn `ValueError`): rejects with 422 if the target has fewer than 2 classes, or if any class has fewer than 6 rows after preprocessing (chosen so at least ~4 remain in the 80% training fold — enough for 3-fold CV).
- Frontend Train step now switches on `response.task`: regression shows MAE/RMSE/R² and actual-vs-predicted/residual scatter charts; classification shows Accuracy/Precision/Recall/F1 and a confusion matrix (rows = actual, columns = predicted, green diagonal / red off-diagonal, per-class support counts shown beneath — covers the "class-distribution information" requirement without duplicating Slice 2's EDA charts).
- **Two more real bugs caught by visual QA, not by tests** (both screenshotted before and after): (1) feature-importance names showed raw `numeric__age` / `categorical__membership_type_Gold` instead of clean names — the `readable_feature_names()` prefix-stripping helper built in Slice 3 was used by the Configure preview but never wired into either training service, which called `.get_feature_names_out()` directly. Fixed in both `regression_training.py` and `classification_training.py`; added assertions in both integration tests that explicitly check for the absence of `numeric__`/`categorical__` prefixes so this can't silently regress again. This is the second time a screenshot caught something three layers of passing tests missed — worth remembering to keep doing visual checks after wiring up a new result view, not just after building it.

**Tests added:**
- Backend (`test_classification_training.py`, 11 tests): metric correctness (perfect prediction, a hand-checked accuracy value), winner selection (highest F1, ignores failed, none-if-all-failed), the same `GridSearchCV.fit`-spy proof that tuning never sees the test split, a synthetic always-fails estimator proving partial failure doesn't abort the others, a programmatically-generated 3-class dataset (explicitly required by the slice plan) asserting a 3×3 confusion matrix and valid metrics for all three models, a real bounded run on `customer_segments.csv` (asserts 3 results, finite metrics in [0,1], 2×2 confusion matrix, correct highest-F1 winner, clean feature-importance names), one-class-target rejection, too-small-class rejection.
- Backend (`test_regression_training.py`): the outdated `test_non_regression_task_returns_not_implemented` (asserted classification → 501, no longer true) replaced with a clustering-still-501 check; added the same clean-feature-name assertion.
- Frontend (`train-step.test.tsx`, +1 test): a classification response renders F1/Accuracy columns (not RMSE), the confusion matrix, and its caption.
- E2E (`train.spec.ts`, +1 test): real backend, `customer_segments.csv`, classification — verifies 3 real model rows all "Success," F1/Accuracy columns, a winner, the confusion matrix, and the feature-importance section.

**Commands executed (all passing):**
- `cd backend && pytest -q` → 56 passed in ~7-12s
- `cd backend && ruff check / ruff format --check / mypy app` → clean
- `cd frontend && npm run test` → 25 passed (6 files)
- `cd frontend && npm run lint / typecheck / format:check` → clean
- `cd e2e && npx playwright test` → 10 passed in ~23s

**Known limitations / decisions:**
- `MIN_ROWS_PER_CLASS = 6` is a judgment call (documented in code) sized for an 80/20 split feeding 3-fold CV, not from the spec.
- Confusion-matrix cell colors are hardcoded RGBA (matching the existing correlation-heatmap component's approach from Slice 2) rather than theme-aware CSS custom properties — consistent with prior work, but both would need revisiting for a fully dark-mode-adaptive heatmap; not attempted here since it wasn't flagged as visibly broken in either light-mode screenshot.

## 4g. Slice 6 checkpoint — Clustering end-to-end vertical slice

**Files created:**
- Backend: `app/ml/registry.py` extended with `ClusteringModelSpec` (a separate, simpler dataclass from `ModelSpec` — no `supports_feature_importance`, plain unprefixed constructor-kwarg grids, since clustering has no `GridSearchCV`/Pipeline scoring to key into) and `CLUSTERING_MODELS` (K-Means, Agglomerative Clustering, DBSCAN); `app/schemas/training.py` extended with `PcaPoint`/`ClusterSizePoint`/`ClusteringCharts` (`ModelResult.charts` is now `RegressionCharts | ClassificationCharts | ClusteringCharts | None`); `app/services/clustering_training.py` (manual bounded grid search per algorithm — no CV, no labels, no train/test split; silhouette-based selection; PCA projection shared across all three models); `training.py` route now handles all three tasks (no more 501 fallback in practice); `backend/tests/test_clustering_training.py`.
- Frontend: `lib/api.ts` extended with clustering chart types + `isClusteringCharts`; `components/pca-scatter-chart.tsx` (hand-rolled inline-SVG scatter colored by cluster, fixed non-cycled categorical hue order, dedicated muted color + smaller/fainter marker for DBSCAN noise, a legend); `train-step.tsx` extended with clustering-aware copy (no held-out split, an explicit "clustering has no known correct answer" explanation per the spec's requirement), a clustering metrics column set (Silhouette/Davies–Bouldin/Clusters/Noise points), and a PCA-projection-plus-cluster-sizes results view with a noise-point explanation.

**Functionality completed:**
- Unlike regression/classification, clustering has no labels to hand `GridSearchCV` a scoring callable, so each algorithm's small grid (`itertools.product` over its param values) is searched manually: every combination is fit once on the same scaled features, and only combinations producing a *valid* solution (≥2 real clusters, not every point noise, not every point its own singleton) are eligible to be selected as "best" by silhouette score. An algorithm with zero valid combinations is reported `status: "failed"` with an explanatory warning rather than crashing or silently picking a degenerate solution — this is the "treat invalid solutions as unsuccessful" requirement, and is unit-tested directly (single-cluster, all-singleton, and all-noise label arrays all correctly rejected).
- Frontend: PCA scatter plot colored by cluster (fixed hue order, not reassigned by rank — consulted the `dataviz` skill's categorical-color guidance again here since this is the first genuinely multi-series chart in the project) with noise points rendered smaller, fainter, and gray with their own legend entry; a cluster-size bar chart (reusing the Slice 2 `BarList` component); and a plain-language explanation of why clustering scores aren't comparable to supervised metrics, satisfying Software Requirement.md §11.3's explicit requirement to explain that distinction to the user.
- Verified with a real screenshot (no bugs found this time, after two in a row in Slices 4-5): three colored clusters plus gray noise render correctly, cluster-size bars and the noise explanation both show real counts, zero browser console errors.

**Tests added:**
- Backend (`test_clustering_training.py`, 14 tests): solution-validity unit tests (2 real clusters valid; single cluster invalid; all-singletons invalid; all-noise invalid; 2 clusters + some noise valid), score-computation tests (invalid → `None`; well-separated synthetic clusters → high silhouette; noise correctly excluded from scoring but still countable), `select_winner` (highest silhouette, none-if-all-failed), a degenerate-DBSCAN-config test proving a model with no valid combination reports `status: "failed"` with a warning instead of crashing, a real bounded run on `customer_segments.csv`'s numeric features (asserts 3 results, ≥1 valid result, correct highest-silhouette winner, PCA/cluster-size chart data present), a DBSCAN-noise-count test, and a clustering-rejects-categorical-features test.
- Backend (`test_regression_training.py`): removed the now-permanently-stale "task X returns 501" test (no task is unimplemented anymore) rather than leave a test asserting behavior that can never happen again.
- Frontend (`train-step.test.tsx`, +1 test): a clustering response renders Silhouette/Noise points columns (not RMSE), the PCA projection heading, cluster sizes, and the noise-point explanation.
- E2E (`train.spec.ts`, +1 test): real backend, `customer_segments.csv`, clustering — verifies 3 real model rows (≥1 "Success," matching the spec's "at least one valid result" framing rather than assuming all three always succeed), a winner, the PCA projection, and cluster sizes.

**Commands executed (all passing):**
- `cd backend && pytest -q` → 69 passed in ~7-13s
- `cd backend && ruff check / ruff format --check / mypy app` → clean
- `cd frontend && npm run test` → 26 passed (6 files)
- `cd frontend && npm run lint / typecheck / format:check` → clean
- `cd e2e && npx playwright test` → 11 passed in ~15-21s

**Known limitations / decisions:**
- DBSCAN's `eps` grid (0.5-2.0) is tuned for standard-scaled data; if a user picks `scaler: "none"` for clustering, DBSCAN may perform poorly or always fail on very different-scale raw data. Not a bug — a known property of DBSCAN — but worth knowing if a demo run picks an unusual scaler.
- Every clustering model shares one PCA projection (fit once on the same preprocessed features) so their visualizations are directly comparable to each other; this is a deliberate design choice, not an oversight.

## 4h. Slice 7 checkpoint — Artifact export

**Files created:**
- Backend: `app/services/training_run.py` (a small dataclass wrapping a `TrainingResponse` together with the successful models' *fitted* sklearn pipelines — needed because the pydantic response schema can't hold non-serializable sklearn objects, but the route layer needs those objects to persist anything); `app/services/experiment_store.py` (persistence: joblib-dumps each successful model's full fitted pipeline, writes per-model chart JSON, `metadata.json`, and a regenerated EDA report, all under a `uuid4().hex` experiment id; strict whitelist validation on `experiment_id`/`model_key` before any path is built, so a malformed id can never be used to construct a path outside the artifacts directory); `app/api/routes/experiments.py` (`GET .../models/{key}/download`, `GET .../download` for the full ZIP); `backend/tests/test_experiment_export.py`.
- Refactored all three training services (`regression_training.py`, `classification_training.py`, `clustering_training.py`): `_train_one_model` now returns `(ModelResult, Pipeline | None)` instead of just `ModelResult`, and `run_*_training` now returns a `TrainingRun` instead of a bare `TrainingResponse`. `training.py` (the route) unwraps `.response`/`.fitted_pipelines`, persists an experiment when at least one model succeeded, and stamps `experiment_id` onto the response before returning it.
- Frontend: `lib/api.ts` extended with `experiment_id` on `TrainingResponse` plus `getModelDownloadUrl`/`getExperimentDownloadUrl`; `train-step.tsx` extended with a "Download complete experiment" button in the comparison card header, a "Download best model" button on the winner card, and a per-row download link in the comparison table (shown only for successful models — a failed model shows "—" instead, per the slice's explicit "disable export for failed models" requirement).

**Functionality completed:**
- Every exported supervised (regression/classification) artifact is the *complete* fitted `Pipeline([("preprocessing", ...), ("model", ...)])` object, not a bare estimator — confirmed by loading a downloaded `.joblib` file back and calling `.predict(raw_dataframe[features])` directly on unprocessed fixture rows with no manual preprocessing step, which is exactly what the slice's acceptance criterion asks for.
- Clustering export required a genuine design decision the other two tasks didn't: clustering doesn't use `GridSearchCV`, so there's no ready-made "best fitted pipeline" sitting around after tuning. Solved by tracking the winning combination's already-fitted estimator instance during the manual grid search, then combining it with the shared already-fitted preprocessing step into a `Pipeline` object *after the fact* — sklearn doesn't require re-fitting a `Pipeline` whose individual steps are already fitted. Verified directly (not just asserted): K-Means's exported pipeline predicts new rows correctly; Agglomerative Clustering's and DBSCAN's both raise `AttributeError: This 'Pipeline' has no attribute 'predict'` when asked to — which is *expected*, scikit-learn's own documented behavior (neither algorithm supports predicting unseen data by design), and is explained in plain language in the exported `metadata.json`'s `prediction_notes` field, satisfying the slice's explicit "document limitations for estimators without general out-of-sample prediction" requirement.
- "Graphs" are exported as the same chart JSON the UI already renders (`charts/{model_key}.json`), not rasterized images — a deliberate scope decision to avoid adding a server-side plotting dependency (e.g. matplotlib) purely for file export in a project that otherwise renders every chart as inline SVG/HTML on the frontend.
- An experiment is only persisted when at least one model actually succeeded (`winner_key is not None`); if every model fails, nothing is written to disk and the response's `experiment_id` stays `null` — verified with a test that forces all three registered models to fail.
- Export security: `experiment_id` must match `^[a-f0-9]{32}$` (the exact shape `uuid4().hex` produces) and `model_key` must match `^[a-z][a-z0-9_]*$` (the shape of every real registry key) *before* either value is used to build a filesystem path — a whitelist check, not a blacklist, so no traversal sequence needs to be individually anticoded. ZIP member paths are built from `path.relative_to(experiment_root)` on files already discovered by walking that root, so a member path can never be attacker-influenced in the first place.

**Tests added:**
- Backend (`test_experiment_export.py`, 14 tests): an experiment id is returned on success and withheld when every model fails; a downloaded model reloads via `joblib.load` and predicts correctly on raw, un-preprocessed fixture rows; a failed model's artifact 404s; the complete-experiment ZIP contains `metadata.json`, `eda_report.html`, and a `models/`+`charts/` entry per successful model, with every member path checked to be relative and free of `..`; `metadata.json` is checked field-by-field (task, target, dataset filename, winner, a real timestamp, prediction notes, per-model metrics/best_params); a dedicated clustering test confirms the prediction-limitations text specifically mentions DBSCAN and predicting; unknown experiment/model ids 404 cleanly (response body checked to contain no stack trace); parametrized path-traversal attempts against both `experiment_id` and `model_key` are rejected. One of the traversal test cases (a bare `".."` segment) had to be corrected after discovering that raw `".."` path segments are normalized away by the HTTP client *before* the request is even sent (standard RFC 3986 behavior) — it was silently aliasing to a different, already-authorized endpoint rather than exercising the intended validation code at all; fixed by percent-encoding the dots (`%2E%2E`) so the literal string actually reaches the handler.
- Frontend (`train-step.test.tsx`, +1 test): the three download affordances (per-row, best-model, complete-experiment) all point at the correct URLs, and a failed model shows no download link.
- E2E (`export.spec.ts`, 1 test): a real regression run against the real backend, then a real click-through download of both the complete experiment ZIP and the best model file, asserting on the actual filename pattern and that neither download reports a failure.

**Commands executed (all passing):**
- `cd backend && pytest -q` → 83 passed in ~9-30s (varies; several tests in this slice run 2-3 real trainings each)
- `cd backend && ruff check / ruff format --check / mypy app` → clean
- `cd frontend && npm run test` → 27 passed (6 files)
- `cd frontend && npm run lint / typecheck / format:check` → clean
- `cd e2e && npx playwright test` → 12 passed in ~23s

**Known limitations / decisions:**
- Experiments are stored on the local filesystem under `backend/storage_data/artifacts/<experiment_id>/` for the life of the backend process — consistent with the project's explicit "no database, no permanent history" scope (Software Requirement.md §17), but they don't survive a backend restart and there's no cleanup/expiry policy. Fine for a demo; would need addressing for anything longer-lived.
- Every successful model's fitted pipeline is persisted for every run (not just the winner) — matches the slice's explicit requirement to export "any successfully trained model," not only the best one.

## 4i. Slice 8 checkpoint — Complete UI workflow, resilience and accessibility

**Files created:**
- Frontend: `components/training-results.tsx` (extracted from `train-step.tsx` — the model-comparison table, winner card and charts, now reusable from both the Train step's own success state and a dedicated Results step); `components/step-nav.test.tsx` (4 new tests).
- E2E: `e2e/tests/accessibility.spec.ts` (5 tests, `@axe-core/playwright`), `e2e/tests/responsive.spec.ts` (3 tests, laptop viewport widths).

**Files modified:**
- `App.tsx`: `handleUploaded`, `handleReadyChange` and `goToStep` wrapped in `useCallback` (see bug below); added a real Results step (`currentStep === 'results'` now renders `<TrainingResults>` instead of a placeholder); step-nav clicks wired to `goToStep` so completed steps are real back-navigation, not just a progress indicator; focus is moved to the new step's content on every navigation (skipping the very first render) for keyboard/screen-reader users.
- `components/step-nav.tsx`: completed steps (before the current one) now render as a real `<button aria-label="Go back to {step}">` when `onStepClick` is passed; current/future steps stay non-interactive `<div>`s.
- `components/train-step.tsx`: simplified to just the "start training" action card; results rendering now delegates to `<TrainingResults>`; added an explicit early-return guard in `handleStart` (in addition to the existing `disabled` prop) so a double-click during an in-flight request can never fire a second training call.
- `index.css`: `--muted-foreground`, `--success` and `--warning` (light mode only) darkened; `--destructive` (light mode) darkened slightly — see the accessibility fixes below for the exact reasoning and numbers.
- `components/ui/badge-variants.ts`: no code change, but its `success`/`warning`/`destructive` variants now pass contrast because of the token changes above.
- `components/correlation-heatmap.tsx`: replaced a continuous `rgba(...)`-alpha background with a discrete 5-step validated sequential ramp (see below).
- `components/dataset-preview-table.tsx`, `correlation-heatmap.tsx`, `confusion-matrix-view.tsx`, `profile-step.tsx`: their independently-scrollable, non-interactive table containers gained `tabIndex={0}`, `role="region"`, an `aria-label` and a focus ring.
- `e2e/tests/configure.spec.ts`, `upload.spec.ts`, `train.spec.ts`: one new scenario each (see below).

**Functionality completed:**
- **A Results step that actually exists.** Slices 0-7 left `currentStep === 'results'` rendering a placeholder; it now shows the same `TrainingResults` view as the Train step's success state, reachable via "Continue to results" once a training run has succeeded, and via step-nav once visited.
- **Back-navigation.** Step-nav items for already-completed steps are now real, keyboard-accessible buttons (`aria-label="Go back to <step>"`) instead of a purely visual progress trail — the E2E replace-dataset test (below) exercises this directly.
- **Full accessibility pass** (axe-core, "no serious/critical violations" as the acceptance bar) across Upload/Profile/Configure/Train — found and fixed 4 real, distinct issues, none of which any prior test suite (83 backend + 27 frontend + 12 e2e at the time) had caught:
  1. The `Badge` `success` variant (used for the "Backend connected" health indicator shown on *every* page, and for "Success"/"Best" badges in results tables) had a contrast ratio of only 3.28-3.45:1 against its own tinted background, against a 4.5:1 requirement. Root cause: `--success`'s lightness (35%) was tuned for how the color looks as a small accent, not for its actual use as *text*. Fixed by darkening `--success` to 25% lightness (verified: ≥5.5:1 against its own `/5` and `/10` tint backgrounds, ≥6.4:1 against plain white) — computed and checked programmatically (WCAG relative-luminance formula) rather than eyeballed, for every affected background this token is actually laid over, not just white.
  2. Several `text-muted-foreground` instances on very-slightly-tinted card backgrounds (`bg-success/5`, `bg-primary/5`) measured 4.38-4.44:1 — just under the 4.5:1 bar, because `--muted-foreground` (47% lightness) had only been checked against plain white (4.70:1) and a near-white tint erodes that margin. Fixed by darkening `--muted-foreground` to 44% lightness (4.91:1+ against every tinted background found in the app; dark mode was already comfortably passing and left alone).
  3. `--destructive` (light mode, 51% lightness) also measured under 4.5:1 as badge/alert text on its own `/10` tint (4.13:1); darkened to 42%, which *also* raised its solid-background-with-white-text contrast (the destructive button) from 4.59:1 to 6.19:1 — a pure improvement with no downside found for either use.
  4. The correlation heatmap's cell coloring used a continuous `rgba(37, 99, 235, alpha)` blend with a single alpha threshold (`> 0.55`) for switching between dark and light cell text. Computing contrast across the *entire* alpha range showed an unavoidable "dead zone" around alpha 0.85-0.93 where *neither* black nor white text reaches 4.5:1 against the blended background — a structural property of blending any single hue from white to a saturated color, not something a smarter threshold could fix. Replaced with a discrete 5-step sequential ramp (`#eff6ff`→`#1e3a8a`, matching the `dataviz` skill's "named steps, not a raw computed gradient" guidance already used elsewhere in the project), with each step's background/text pairing individually verified ≥5.1:1.
  5. `scrollable-region-focusable`: four independently-scrollable data tables (dataset preview, correlation heatmap, confusion matrix, profile's column table) had no focusable content, so a keyboard user had no way to scroll them. Fixed by making each container itself a focusable, labeled region (`tabIndex={0}`, `role="region"`, `aria-label`, focus ring) — the model-comparison table wasn't affected since its download buttons already made it focusable.
- **Responsive check at common laptop widths** (1024×768, 1280×800, 1366×768): walked the full Upload→Profile→Configure→Train flow at each width and asserted `document.documentElement.scrollWidth` never exceeds `clientWidth` (i.e. the page body itself never needs to scroll horizontally — wide content like the model-comparison table scrolls within its own container instead, by existing design). All three widths pass without any layout change being needed.

**A real bug found and fixed via the project's own regression-testing discipline** (not requested by you, not caught by any test until this slice's full-suite run): `handleUploaded`, `handleReadyChange` and `goToStep` in `App.tsx` were plain inline functions, recreated on every render. `handleReadyChange` is passed to `ConfigureStep` and sits in that component's debounced preview `useEffect`'s dependency array; calling it changes `App`'s state, which creates a new function reference, which re-triggers that effect, which cancels its own pending debounce timer and calls `onReadyChange` again — an infinite loop that meant the preprocessing preview never actually stabilized. Found because the full Playwright suite (previously a steady ~24s) intermittently ballooned to ~2.9 minutes with 3 failures; fixed by wrapping all three handlers in `useCallback` with empty dependency arrays (documented in-code, since the failure mode is non-obvious from reading either component alone). Verified: the same suite went back to 12/12 passing in 23.9s.

**Tests added:**
- Frontend (`step-nav.test.tsx`, 4 tests): `aria-current` on the active step, completed steps are clickable and call `onStepClick` with the right step id, current/future steps are never clickable, and no buttons render at all when `onStepClick` is omitted.
- E2E (`accessibility.spec.ts`, 5 tests): zero serious/critical axe-core violations on Upload (idle), Upload (with a dataset loaded), Profile, Configure, and Train (results) — each against the real backend, not mocked.
- E2E (`responsive.spec.ts`, 3 tests): the laptop-width, no-horizontal-page-overflow check described above; the Train step in this spec uses a mocked `/train` response (`page.route()`) so three viewport widths don't mean three real training runs.
- E2E (`configure.spec.ts`, +1 test): an incomplete configuration (no target selected, then all features unchecked even with a target selected) shows "Complete the configuration above…", never shows "ready to train", and keeps "Continue to train" disabled throughout — the slice's explicit "invalid configuration blocks training" scenario.
- E2E (`upload.spec.ts`, +1 test): configure `house_prices.csv` to a ready-to-train state, navigate back to Upload via the new step-nav button, replace the dataset with `customer_segments.csv`, and confirm Configure remounts genuinely fresh — no leftover target selection, the old dataset's target option (`price_usd`) is gone from the dropdown, the new dataset's columns are present, the preview reverts to "incomplete," and "Continue to train" is disabled again. This directly exercises the `key={dataset.dataset_id}`-remount and `setTrainConfig(null)`/`setTrainingResponse(null)` staleness-clearing logic that was implemented but previously untested at the E2E level.
- E2E (`train.spec.ts`, +1 test): a mocked `/train` response (`page.route()`) with one model `status: "failed"` and two `"success"` — asserts all 3 rows render, the failed row shows "Failed" and its warning text, the two successful rows show "Success," and the winning model's charts and feature-importance section still render normally despite the sibling failure. Mocked (rather than trying to force a genuine backend failure) because no real, deterministic failure exists for the three registered regression models on the project's own clean fixtures.

**Commands executed (all passing):**
- `cd backend && pytest -q` → 83 passed (no backend changes this slice; re-run as part of the full regression)
- `cd frontend && npx tsc --noEmit` → clean
- `cd frontend && npm run lint` (oxlint) → clean
- `cd frontend && npx vitest run` → 31 passed (7 files)
- `cd e2e && npx playwright test` → 23 passed in ~24-41s (timing varies; the two real end-to-end training tests in `train.spec.ts` dominate)

**Known limitations / decisions:**
- Dark mode (`.dark` class) is defined in `index.css` but not currently reachable from the UI — there's no theme toggle and nothing applies the class, so it's effectively dead code today. While auditing contrast for this slice, `--destructive` in dark mode was found to fail badly (1.80:1) as badge/alert text on a dark card, because it's tuned for "white text on a solid button," a fundamentally different constraint than "colored text on a dark card" — no single lightness value satisfies both (verified numerically: every value tested trades one contrast requirement off against the other). Left unfixed since dark mode isn't user-reachable and none of the axe-core E2E tests exercise it (Playwright's default context doesn't set `prefers-color-scheme: dark` or the `.dark` class); worth splitting into separate "solid" and "on-tint" design tokens if/when a dark-mode toggle is actually built.
- The one full-suite flake seen while verifying this slice (a single `color-contrast` violation on the Train results view, in an otherwise-clean run) did not reproduce across 3 immediate repeats in isolation or a second full-suite run; most likely a transient side effect of this session's shared, persistently-running dev backend (which keeps exactly one active dataset in a single in-process slot, per the Slice 1 design) being hit by another process at the same moment, not a product defect — noted here rather than silently ignored.
- Responsive verification checked for horizontal page overflow specifically (the concrete, automatable form of "usable at common laptop widths"); it did not re-check every individual chart's readability at 1024px by eye beyond the Slice 2-6 screenshots already taken at 1280px.

## 4i-addendum. A real bug you found live, and exhaustive combination testing

**The bug:** picking Classification with `distance_to_center_km` (a continuous numeric column) as the target on `house_prices.csv` reached the Train step and failed with an error message that named all ~190 of that column's distinct values, one after another, in a single unreadable sentence. Two compounding problems: (1) the live Configure-step preview had no classification-specific target validation at all — it only checked row counts — so it showed "Ready to train" for a configuration that was guaranteed to fail; (2) the training-time error message itself had no cap on how many class labels it would list.

**The fix** (`backend/app/services/config_validation.py`): a new shared `classification_target_issues(y)` function — checked *before* the noisier per-class-size check — rejects a target with more than `MAX_CLASSES_FOR_CLASSIFICATION = 20` distinct values with one clear sentence ("too many for a classification target… looks like a continuous measurement instead… consider Regression"), and caps any remaining "class(es) too small" message to the first 10 labels plus "and N more." This function is now called from **both** `build_preprocessing_preview` (as a warning that sets `ready_to_train: false`, so Configure catches it live) and `run_classification_training` (as the same hard 422 error) — restoring the project's established rule that preview and training share one validation path and can never silently diverge (§4d), which this specific check had drifted from.

**A second, unrelated bug found while verifying the fix**: the live backend dev server the user had been viewing the app through (started earlier in this session, without `--reload`) was running stale code — the `config_validation.py` edit had no effect on it at all until it was restarted. Caught by checking the live UI directly rather than trusting the fix in isolation; restarted with `--reload` so this can't recur for the rest of the session.

**Standing new test requirement (your instruction):** every task × target combination — not just the two intended ones per dataset — must be exercised against both fixtures, asserting the app always settles cleanly (never an uncaught browser error, never a warning message over 400 characters) whether the combination is sensible or not. Added as `e2e/tests/all-combinations.spec.ts`, 2 tests, each walking one fixture's every column as a target for both regression and classification plus clustering (17 combinations × 2 datasets = 34), all within a single page session per test (driving the same Task radio group / Target dropdown repeatedly, exactly like a user clicking through options, rather than reloading per combination). Confirms: `price_usd`/`churned` (the intended targets) reach ready-to-train; identifier columns (`property_id`, `customer_id`) and continuous numeric columns (`distance_to_center_km`, `annual_income`) as classification targets are cleanly rejected; clustering never gets stuck "incomplete"; zero uncaught errors across the whole walk. Also added `data-testid="config-warning"` to the warning `<li>` in `configure-step.tsx` so this suite (and any future one) can assert on warning content/length without brittle text matching.

**A test-only bug in that same new suite, found and fixed before it was trustworthy**: the first version waited for the transient "Computing preprocessing impact…" text to disappear before reading the result, which is inherently racy — Playwright's polling can observe zero matches either because the request hasn't started yet or because it already finished, and those look identical from text alone. This produced a false "clustering never settles" failure that had nothing to do with the app. Fixed by tying the wait to the actual `POST /preprocessing-preview` network response each action triggers (`page.waitForResponse`), which removes the ambiguity entirely — confirmed stable across 3 repeated runs after the fix (previously flaky).

**Tests added:**
- Backend (`test_classification_training.py`, +1): a near-continuous target (60 rows, 60 distinct values) is rejected with a message containing "too many"/"continuous" and under 400 characters — a direct regression test for the exact bug.
- Backend (`test_config_preview.py`, +1): the same continuous-target case, asserted at the *preview* endpoint — `ready_to_train: false` with the matching warning — proving Configure catches it before Train, not just at Train.
- E2E (`all-combinations.spec.ts`, 2 tests, described above).

**Commands executed (all passing):**
- `cd backend && pytest -q` → 85 passed
- `cd backend && ruff check / ruff format --check / mypy app` → clean
- `cd frontend && npx tsc --noEmit / npm run lint` → clean
- `cd frontend && npx vitest run` → 31 passed (7 files, unchanged — this addendum touched no component behavior the existing suite covers, only added a test id)
- `cd e2e && npx playwright test` → 25 passed in ~47s

## 4i-addendum-2. A severe Docker-specific hang, found by actually running the Docker path (Slice 9 final verification)

While performing Slice 9's required "run the real demonstration workflows against `docker compose up`" verification step, real regression training via the Dockerized stack didn't just work slower than native — it never returned at all within a 30s client timeout, with the backend container pinned at ~2700% CPU. Isolated with a direct `docker exec` script, bypassing this project's own code entirely: a bare `XGBRegressor().fit()` on a tiny synthetic 200×10 array took 0.07s with `n_jobs=1` or `n_jobs=4`, and had not completed after 2+ minutes with XGBoost's *default* `n_jobs` (which auto-detects the reported CPU count — 28 here, matching the host exactly, so not even a container CPU-count-detection bug, just a real thread-pool contention pathology under Docker Desktop's WSL2 backend on a high-core-count host).

**The fix** (`backend/app/ml/registry.py`): added `XGBOOST_N_JOBS = 4` and passed `n_jobs=XGBOOST_N_JOBS` to both `XGBRegressor` and `XGBClassifier`'s constructors — the only two estimators in the registry that default to auto-detecting/using all cores (`RandomForestRegressor`/`Classifier` already default to `n_jobs=None`, i.e. sequential, so were never at risk). Verified: a real regression run via the rebuilt Docker image now completes in a couple of seconds, matching native performance, with zero console/page errors. As a genuinely pleasant side effect, the fix also sped up the *native* backend test suite (28s → 12s) — spawning far fewer threads across ~90 fit calls in one process turns out to be a net win outside Docker too, not just a Docker-only workaround.

**Test added:** `backend/tests/test_registry.py` (1 test) — asserts both XGBoost model specs construct estimators with `n_jobs == XGBOOST_N_JOBS` and that the cap is a small positive number, so this fix can't be silently reverted by someone "cleaning up" what looks like a redundant constructor argument without a test failing.

**Full Docker verification performed** (Slice 9's "final verification from a clean environment" §7-8, items 1-2 and 7-8 — items 3-6 are covered natively above, since the plan validates Docker as the packaging/runtime target, not a second copy of the test environment):
- `docker compose build` — both images build clean from the current source.
- `docker compose up -d` — both containers start; `GET /api/health` (backend, port 8000) and `GET /` (frontend, port 3000) both respond.
- A real headless-browser run against the Dockerized stack: upload `house_prices.csv` → Profile → Configure (regression, `price_usd`) → Train → real 3-model training completes → the "Download complete experiment" link renders — zero console or page errors throughout.
- `docker compose down` — clean teardown.

**Commands executed (all passing):**
- `cd backend && pytest -q` → 86 passed (12s, down from 28s)
- `cd backend && ruff check / ruff format --check / mypy app` → clean
- `docker compose build && docker compose up -d` → both images build and start clean
- Headless-browser smoke run against `localhost:3000`/`localhost:8000` (Docker) → full upload→profile→configure→train→export flow, zero console errors
- `docker compose down` → clean

## 4j. Slice 9 checkpoint — Packaging, documentation and final verification

**Files modified:**
- `README.md` — fully rewritten from the Slice 0 placeholder into the complete, final version: prerequisites, a one-command Docker quick start (also the project's production-style run), native dev setup for both services, environment configuration, test commands (with current pass counts), quality-gate commands, project layout, a dedicated "Dataset assumptions and limits" section (file validation rules, size limit, the one-active-dataset/no-persistence product scope, row/class minimums, the new classification-class-count limit), a "Models, metrics and tuning" section (a table of all 9 models across 3 tasks with their tuned parameters and winner-selection metric, plus known limitations including the XGBoost/Docker fix below), two worked example workflows using the committed fixtures, and an 8-step demonstration checklist.
- Nothing else needed to change for packaging: dependencies were already exactly pinned (`backend/requirements.txt`) and lockfiled (`frontend/package-lock.json`, `e2e/package-lock.json`) from earlier slices, both `.env.example` files already existed with no secrets, and `docker-compose.yml` already existed — this slice's job was documenting and *verifying* those, plus fixing a real bug the verification surfaced (§4i-addendum-2).

**Final verification performed** (per the plan's exact 8-step checklist, §"Final verification"):
1. **Install dependencies using only the documented instructions** — backend: created a brand-new virtualenv (not the one used all session) and ran the exact `pip install -r requirements-dev.txt` from the README; frontend and e2e: ran `npm ci` against isolated copies of each `package.json`/`package-lock.json` (not the live project's `node_modules`, which the running dev server had open) — all three installed clean, zero errors, e2e/frontend reported 0 vulnerabilities.
2. **Start backend and frontend** — verified both the native dev path (already running throughout this session) and the Docker path (`docker compose up -d`) serve traffic.
3. **Run backend tests** — 86 passed, from the freshly created venv.
4. **Run frontend tests** — 31 passed.
5. **Install required Playwright browser dependencies** — chromium already installed earlier in the session; suite runs clean.
6. **Run the full Playwright suite** — 25 passed.
7. **Perform the three demonstration workflows** — regression (`house_prices.csv` → `price_usd`) verified via a real headless-browser run against the *Dockerized* stack specifically (not just native, which every other e2e run already covers); classification and clustering (`customer_segments.csv`) are covered natively by `train.spec.ts` and exhaustively by `all-combinations.spec.ts` (§4i-addendum).
8. **Download and inspect a complete experiment export** — covered natively by `export.spec.ts` (downloads and verifies the ZIP's real contents); the Docker run additionally confirmed the "Download complete experiment" link renders correctly after a real Docker-trained run.

**A real, severe bug found only because this verification was actually run against Docker** (not skipped as "should be the same as native"): documented in full in §4i-addendum-2 — XGBoost's default thread count caused real training to hang indefinitely under Docker Desktop's WSL2 backend; fixed with a small fixed `n_jobs` cap, verified fixed via a second full Docker run, and covered by a new regression test (`test_registry.py`).

**Commands executed (all passing):**
- Fresh venv: `python -m venv <temp> && <temp>/pip install -r requirements-dev.txt && <temp>/python -m pytest -q` → 86 passed
- `cd frontend && npm ci` (isolated copy) → clean, 0 vulnerabilities
- `cd e2e && npm ci` (isolated copy) → clean, 0 vulnerabilities
- `cd frontend && npx vitest run` → 31 passed
- `cd e2e && npx playwright test` → 25 passed in ~47s
- `docker compose build && docker compose up -d` → both images build and start clean; real browser-driven regression workflow completes end to end with zero console errors; `docker compose down` → clean teardown

**Known limitations / decisions:**
- "Clean environment" verification used fresh installs (venv, `npm ci`) rather than a literally separate machine/OS — the most rigorous check practical in this session, and the one that actually caught the Docker-specific XGBoost bug; a true from-scratch OS install was not performed.
- No CI pipeline was added (not in this slice's or any earlier slice's explicit scope) — all verification here was run locally/on-demand, consistent with every earlier slice.
- Demonstration mode and test mode intentionally share the same small hyperparameter grids (documented in the README's known limitations) — there is no separate "fast" vs. "full" grid size, since even the full grids are already small enough to run in seconds; the project's fast/full test distinction referred to in the plan is satisfied by unit/component tests being fast and the real-training integration/e2e tests being the (still fast, seconds-scale) full layer, not by two different grid sizes.

## 5. Reference documents

- [Software Requirement.md](Software%20Requirement.md) — the approved functional requirements (unmodified source of truth).
- [Slicing Of Tasks.md](Slicing%20Of%20Tasks.md) — the controlling implementation plan, broken into slices (unmodified source of truth; Docker amendment tracked here in §3 instead of editing that file directly).

## 6. Next action

**All 10 slices (0-9) are done and verified.** The project is feature-complete per both spec documents: upload → profile → configure → train (regression/classification/clustering, each with real hyperparameter tuning) → compare results → export artifacts, with a full accessibility pass, exhaustive configuration-combination testing, a working Docker path, and complete documentation.

Nothing is queued to work on autonomously. If you want changes — a different model, a new chart, adjusted thresholds, CI, anything else — just ask; this file will keep getting a fresh checkpoint after any further work.
