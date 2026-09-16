# AutoML Studio

A small end-to-end AutoML demonstration: upload a CSV, profile it, configure a
regression, classification or clustering task, tune and train three models
for that task, compare the results, and export the winner as a ready-to-use
artifact.

> **Live demo:** **[questionnaire-analysis-frontend.onrender.com](https://questionnaire-analysis-frontend.onrender.com/)**
> — hosted on Render's free tier. Free instances sleep after ~15 minutes
> idle, so the first request after a quiet spell can take 30-60s to wake up;
> everything after that is normal speed. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
> for how this is hosted and how to manage it.

## Stack

- **Backend:** Python, FastAPI, pandas, scikit-learn, XGBoost, Joblib
- **Frontend:** React + TypeScript, Vite, Tailwind CSS
- **Tests:** pytest (backend), Vitest + React Testing Library (frontend), Playwright (end-to-end, with axe-core accessibility checks)

## Prerequisites

- Python 3.11+
- Node.js 22+
- Docker Desktop (only needed for the containerized workflow)

## Quick start (one command)

The fastest way to see the whole app running is Docker Compose — it builds
and starts both services with the correct URLs already wired together:

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (health check at `GET /api/health`)

This is also the project's **production-style run**: the frontend is
compiled (`vite build`) and served as static files by nginx, not the dev
server, and the backend runs `uvicorn` without `--reload`.

## Deployment

The live demo above runs as two independent Docker web services on Render
(backend and frontend, deployed separately) rather than `docker compose`,
since Render builds one Dockerfile per service. Full setup instructions,
the exact configuration values, the mistakes that cost the most time getting
there, and how to manage the deployed services (dashboard and CLI) are all in
**[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

## Local development (without Docker)

Two terminals, run from the repository root.

### Backend

```bash
cd backend
python -m venv .venv
./.venv/Scripts/pip install -r requirements-dev.txt   # Windows
# source .venv/bin/activate && pip install -r requirements-dev.txt   # macOS/Linux

./.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

Backend runs at http://localhost:8000.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173 and talks to the backend at
`http://localhost:8000` by default.

### Configuration

Both services read optional environment variables; every default already
works for local development, so `.env` files are only needed to change
something.

```bash
cp backend/.env.example backend/.env      # CORS origins, environment name
cp frontend/.env.example frontend/.env.local   # VITE_API_BASE_URL, if the backend isn't on localhost:8000
```

No secrets are required anywhere in this project (no API keys, no database
credentials, no auth) — both `.env.example` files exist purely as a record
of the two variables that *can* be overridden.

## Tests

```bash
# Backend (88 tests)
cd backend && ./.venv/Scripts/python -m pytest -q

# Frontend (31 tests)
cd frontend && npm run test

# End-to-end (25 tests — starts backend + frontend automatically if they
# aren't already running)
cd e2e && npm install && npx playwright install --with-deps chromium && npx playwright test
```

The end-to-end suite includes at least one real, non-mocked training run per
task (regression/classification/clustering) against the real backend, an
accessibility pass (axe-core, zero serious/critical violations), a
no-horizontal-overflow check at three common laptop widths, and an
exhaustive task × target combination sweep over both fixture datasets (every
column as a target for every task, including deliberately wrong choices like
an identifier or continuous column as a classification target — the app
must always degrade gracefully, never with an ugly error). A couple of
scenarios mock the training response deliberately (a partial model failure,
and the three-viewport responsive check) to stay fast and deterministic —
every task still gets at least one fully real run elsewhere in the suite.

## Quality gates

```bash
# Backend
cd backend && ./.venv/Scripts/python -m ruff check app tests && ./.venv/Scripts/python -m ruff format --check app tests && ./.venv/Scripts/python -m mypy app

# Frontend
cd frontend && npx tsc --noEmit && npm run lint && npm run format:check
```

## Project layout

```
backend/    FastAPI application, ML services, tests
frontend/   React + TypeScript single-page app
e2e/        Playwright end-to-end tests (drives backend + frontend together)
docs/       Requirements, implementation plan, progress log, and the deployment guide
scripts/    Deterministic fixture generator
tests/fixtures/   Committed sample CSVs used by every test layer and the demo below
```

## Dataset assumptions and limits

The backend validates every upload before accepting it:

- File extension must be `.csv`; content must decode as UTF-8 (a UTF-8 BOM
  is tolerated and stripped).
- Maximum file size: **25 MB**.
- The file needs a non-empty header row with no empty or duplicate column
  names, at least one column, and at least one data row.
- Column types are auto-detected (numeric vs. categorical) from the parsed
  data — there's no manual type-override step.

Product-scope limits worth knowing before a demo:

- **One active dataset at a time.** Uploading a new CSV replaces whatever
  was active, including its stored file — there are no accounts, no
  multi-dataset workspace, and no persistent history. This matches the
  project's explicit scope (a single-user demonstration tool, not a
  multi-tenant product).
- **Nothing survives a backend restart.** The active dataset and any trained
  experiment artifacts live only for the life of the backend process
  (in-memory pointer + files under `backend/storage_data/`, not a database).
- **Training needs at least 30 rows** left after preprocessing (missing-value
  rows are always dropped; duplicate rows are dropped if that option is
  left on). Below that, the Configure step reports exactly why the
  configuration isn't ready instead of failing silently. A warning is also
  shown whenever preprocessing would remove more than 30% of the original
  rows.
- **A regression target must be numeric.** A categorical column (a
  neighborhood name, a yes/no flag) picked as a regression target is
  rejected with a clear message rather than reaching training.
- **Classification additionally needs every class to have at least 6 rows**
  after preprocessing (so a stratified 80/20 split still leaves enough of
  the smallest class for 3-fold cross-validation), and at least 2 but no
  more than 20 distinct classes — a target with more than 20 distinct values
  is treated as a continuous measurement, not a category, and is rejected
  with a suggestion to use Regression instead. All three of these checks run
  live in the Configure step, not just at train time, so a bad target/task
  combination is flagged before you ever click Start training.
- **Clustering only uses numeric features** in this version — categorical
  columns are shown but disabled in the feature picker for that task.
- Categorical columns where more than half the values are unique (e.g. an ID
  column) are excluded from the *default* feature selection and from EDA
  frequency charts, since one-hot-encoding them would produce one column per
  row — they can still be added back by hand.

## Models, metrics and tuning

Every task trains and compares exactly three models, each tuned over a
small, bounded hyperparameter grid with `GridSearchCV` (regression/
classification) or a manual grid search (clustering, which has no labels to
score against). All randomness is seeded (`random_state=42`) so a given
dataset and configuration trains identically every run.

| Task | Models | Tuned parameters | Primary metric (winner selection) |
|---|---|---|---|
| Regression | Linear Regression, Random Forest Regressor, XGBoost Regressor | `fit_intercept`; `n_estimators`×`max_depth`; `n_estimators`×`max_depth` | Lowest RMSE on a held-out 20% split |
| Classification | Logistic Regression, Random Forest Classifier, XGBoost Classifier | `C`; `n_estimators`×`max_depth`; `n_estimators`×`max_depth` | Highest weighted F1 on a stratified held-out 20% split |
| Clustering | K-Means, Agglomerative Clustering, DBSCAN | `n_clusters`; `n_clusters`×`linkage`; `eps`×`min_samples` | Highest silhouette score (no held-out split — clustering has no ground truth) |

Full metric sets shown per model: regression reports MAE/RMSE/R²;
classification reports accuracy/weighted precision/weighted recall/weighted
F1 plus a confusion matrix; clustering reports silhouette, Davies–Bouldin,
cluster count and noise-point count (DBSCAN only).

**Known limitations:**

- Grids are intentionally small (2-4 combinations per model) so a full
  three-model comparison finishes in a few seconds for a demo-sized
  dataset — this is a teaching tool, not a production tuning pipeline.
- XGBoost's thread count is deliberately capped (`n_jobs=4` in
  `app/ml/registry.py`) rather than left at its auto-detecting default. On a
  high-core-count host under Docker Desktop's WSL2 backend, the default was
  found to cause severe thread-pool contention — a fit that takes ~0.1s
  natively never completed at all. The cap fixes both environments and, as a
  bonus, also runs faster natively.
- A model that fails to fit is recorded as a failed result with its error
  message rather than aborting the whole run; a winner is still picked from
  whichever models succeeded.
- DBSCAN's `eps` grid (0.5–2.0) is tuned for standard-scaled data; choosing
  `scaler: none` for a clustering task may make DBSCAN perform poorly or
  fail to find any valid clustering.
- Agglomerative Clustering and DBSCAN don't support predicting new, unseen
  rows (this is standard scikit-learn behavior, not a bug in this project) —
  their exported artifacts document this limitation in `metadata.json`
  rather than silently failing later. K-Means and every regression/
  classification model export a fully usable `predict()`-ready pipeline.
- Charts are exported as the same JSON the UI renders from, not rendered
  images — opening them requires reading the JSON or re-importing it into a
  plotting tool, not double-clicking an image file.

## Example workflows

Two committed, deterministic fixture files (`tests/fixtures/`, seed 42) cover
all three tasks:

### `house_prices.csv` — regression

222 rows of synthetic property listings (`area_m2`, `bedrooms`, `age_years`,
`distance_to_center_km`, `neighborhood`, `has_parking` → `price_usd`), with a
noisy-but-learnable linear relationship (R² ≈ 0.87 on this fixture).

1. Upload → Continue to profile → Continue to configure.
2. Task: **Regression** (default). Target: **`price_usd`**. Leave the
   default features and preprocessing as-is.
3. Continue to train → Start training. All three models should succeed in a
   few seconds; XGBoost or Random Forest typically wins on RMSE.
4. Inspect the actual-vs-predicted and residual charts and the feature
   importance bars for the winning model, then download it.

### `customer_segments.csv` — classification and clustering

222 rows of synthetic customer data (`age`, `annual_income`, `spend_score`,
`membership_type`, `region`, `tenure_months` → `churned`), built around 3
well-separated underlying segments (silhouette ≈ 0.58 for the true segment
structure).

**Classification:** Task: **Classification**. Target: **`churned`**. Train —
expect all three models to succeed with a confusion matrix and per-class
support counts for the winner.

**Clustering:** Task: **Clustering** (no target; feature picker
auto-restricts to numeric columns). Train — expect a PCA projection colored
by cluster, cluster-size bars, and (for DBSCAN specifically) a small number
of points marked as noise.

## Demonstration checklist

A short script for a live walkthrough, in order:

1. Open the app (Docker: http://localhost:3000, or the native dev frontend
   at http://localhost:5173) and confirm "Backend connected" shows in the
   header.
2. Upload `tests/fixtures/house_prices.csv`; show the live preview table and
   column type badges.
3. Continue to Profile; show the summary cards, per-column stats, numeric
   distributions, and the correlation heatmap; download the EDA report and
   open it (it's a single self-contained HTML file — no server needed to
   view it later).
4. Continue to Configure; show the task selector, the default feature
   selection excluding the identifier-like `property_id` column, and the
   live "preprocessing impact" panel updating as the target is set.
5. Continue to Train; start training and narrate the three models tuning in
   real time; show the winner highlight, the actual-vs-predicted/residual
   charts, and feature importance.
6. Download the winning model and the complete experiment ZIP; briefly open
   the ZIP to show `metadata.json`, the model file, and the chart JSON.
7. Go back to Upload (via the step nav) and replace the dataset with
   `tests/fixtures/customer_segments.csv`; point out that Configure resets
   cleanly (no stale target or results from the previous run).
8. Repeat Configure → Train once for **Classification** (target `churned`,
   showing the confusion matrix) and once for **Clustering** (showing the
   PCA projection and cluster sizes).

Nothing in this checklist requires an undocumented manual fix — it exercises
only what's described above.

## Status

See [docs/PROGRESS.md](docs/PROGRESS.md) for the detailed, slice-by-slice
implementation log (what was built, what was tested, and known limitations
at each stage), and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for how the live
demo is hosted and managed.
