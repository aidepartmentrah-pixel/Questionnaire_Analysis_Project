# AutoML Demonstration — Claude Implementation Slices

## 1. Purpose of this document

This document divides the approved AutoML demonstration requirements into small, independently verifiable implementation slices. It is intended to be given to Claude as the controlling development plan.

Claude must implement **one slice at a time**, run the required tests, report the results, and stop for review before starting the next slice. A slice is complete only when its acceptance criteria and automated tests pass.

The application uses:

- **Backend:** Python, FastAPI, pandas, scikit-learn, XGBoost and Joblib
- **Frontend:** React with TypeScript
- **Backend testing:** pytest and FastAPI TestClient/httpx
- **Frontend testing:** Vitest and React Testing Library
- **End-to-end UI testing:** Playwright

---

## 2. Rules Claude must follow

1. Read this entire plan and inspect the existing repository before editing.
2. Preserve working code and unrelated user changes.
3. Work on only the current slice.
4. Do not implement features assigned to later slices unless a minimal interface or stub is required.
5. Keep machine-learning logic outside API route handlers.
6. Keep model definitions in a central model registry; do not create nine duplicated training scripts.
7. Use deterministic random seeds in datasets, splitting, models and tuning wherever supported.
8. Add or update tests in the same slice as the behavior being implemented.
9. Run the slice's focused tests, followed by all existing tests.
10. Do not mark a slice complete when tests are skipped, flaky or failing.
11. Do not weaken assertions merely to make tests pass.
12. Never use the final test set during hyperparameter selection.
13. Store uploaded files and generated artifacts in temporary or application-managed directories, not arbitrary user paths.
14. Return readable API errors; do not expose stack traces in the interface.
15. At the end of every slice, report:
    - Files created or changed
    - Functionality completed
    - Tests added
    - Exact test commands executed
    - Passing/failing test counts
    - Known limitations or decisions still pending

---

## 3. Fixed product behavior

The user uploads one CSV and selects one task:

- Regression
- Classification
- Clustering

Selecting a task launches the three models belonging to that task. All three models are hyperparameter-tuned, trained and evaluated. The results are compared, and the best-performing tested model is highlighted.

### Regression models

- Linear Regression
- Random Forest Regressor
- XGBoost Regressor

### Classification models

- Logistic Regression
- Random Forest Classifier
- XGBoost Classifier

### Clustering models

- K-Means
- Agglomerative Clustering
- DBSCAN

### Primary comparison metrics

- Regression: lowest RMSE
- Classification: highest F1-score
- Clustering: highest valid Silhouette score

---

## 4. Test datasets

Create two deterministic synthetic CSV fixtures in `tests/fixtures/`. They are committed test assets, not files generated differently on every test run.

### 4.1 `customer_segments.csv`

Purpose:

- Classification training
- Clustering training after excluding `churned`
- Categorical encoding
- Missing-value removal
- Duplicate detection/removal
- Binary target and class-distribution EDA

Required columns:

| Column | Type | Role |
|---|---|---|
| `customer_id` | string/integer | Identifier to exclude |
| `age` | numeric | Feature |
| `annual_income` | numeric | Feature |
| `spending_score` | numeric | Feature |
| `visits_per_month` | numeric | Feature |
| `membership_type` | categorical | Classification feature; excluded from clustering v1 |
| `region` | categorical | Classification feature; excluded from clustering v1 |
| `churned` | binary integer | Classification target; excluded from clustering |

Fixture characteristics:

- At least 180 rows so 3-fold tuning is stable.
- Both target classes must be represented.
- Features must contain a learnable but imperfect relationship with `churned`.
- Include a small, documented number of missing values.
- Include at least two duplicate rows.
- Clustering numeric features must contain at least three reasonably separable groups.

### 4.2 `house_prices.csv`

Purpose:

- Regression training
- Categorical encoding
- Missing-value removal
- Regression EDA and metrics

Required columns:

| Column | Type | Role |
|---|---|---|
| `property_id` | string/integer | Identifier to exclude |
| `area_m2` | numeric | Feature |
| `bedrooms` | numeric | Feature |
| `age_years` | numeric | Feature |
| `distance_to_center_km` | numeric | Feature |
| `neighborhood` | categorical | Feature |
| `has_parking` | categorical/boolean | Feature |
| `price_usd` | continuous numeric | Regression target |

Fixture characteristics:

- At least 180 rows.
- `price_usd` must follow a learnable but noisy relationship with the features.
- Include a small, documented number of missing values.
- Include at least two duplicate rows.

Add a reproducible fixture-generation script under `scripts/`, but commit the resulting CSV files so tests do not depend on generation at runtime.

---

# 5. Implementation slices

## Slice 0 — Repository foundation and quality gates

### Goal

Create a runnable backend/frontend skeleton and establish testing commands before feature development begins.

### Backend work

- Create the FastAPI application.
- Add `GET /api/health` returning a stable success payload.
- Add configuration for development and tests.
- Configure CORS for the local frontend.
- Establish folders for API routes, schemas, services, model registry and artifact storage.

### Frontend work

- Create the React/TypeScript application shell.
- Add a title and empty five-step layout:
  1. Upload
  2. Profile
  3. Configure
  4. Train
  5. Results
- Add a backend health indicator.

### Testing work

- Configure pytest.
- Configure Vitest and React Testing Library.
- Configure Playwright.
- Add one API health test.
- Add one frontend render test.
- Add one Playwright smoke test that opens the app and sees its title.

### Acceptance criteria

- Backend and frontend start using documented commands.
- Health endpoint returns HTTP 200.
- The application shell renders without console errors.
- Backend, frontend and Playwright smoke tests pass.

### Stop point

Stop after proving the skeleton and all three test layers work.

---

## Slice 1 — Deterministic CSV fixtures and upload workflow

### Goal

Allow the user to upload a valid CSV and inspect its basic structure.

### Backend work

- Create and commit the two fixtures defined in Section 4.
- Add a deterministic fixture-generation script.
- Implement CSV upload and server-side validation.
- Return a dataset/session identifier rather than relying on the original filename.
- Return filename, row count, column count, column names, detected types and preview rows.
- Detect invalid CSV, empty file, header-only file and duplicate column names.
- Restrict upload to a documented size limit and CSV content.

### Frontend work

- Implement drag-and-drop and Browse-button upload.
- Show upload progress/state.
- Display filename, dimensions, detected columns and a scrollable preview table.
- Show friendly validation errors.
- Replacing the file replaces the active dataset.

### Automated tests

Backend tests must cover:

- Successful upload of both fixtures
- Correct dimensions and column metadata
- Empty CSV rejection
- Header-only CSV rejection
- Malformed CSV rejection
- Duplicate-header rejection
- Unsupported extension rejection

Playwright must:

1. Open the application.
2. Upload `customer_segments.csv` through the real file input.
3. Verify its filename, dimensions, columns and preview appear.
4. Upload `house_prices.csv` and verify it replaces the active dataset.

### Acceptance criteria

- Both custom CSV fixtures upload successfully from the UI.
- Invalid files produce understandable messages.
- No ML training exists yet.
- All existing and new tests pass.

---

## Slice 2 — Data profiling and EDA

### Goal

Generate and preview a lightweight EDA report for the active dataset.

### Backend work

- Implement a profiling service returning structured JSON.
- Include dimensions, types, descriptive statistics, unique counts, missing counts/percentages and duplicate count.
- Generate numeric histograms and a numeric correlation matrix.
- Generate frequency information for suitable categorical columns.
- Provide a downloadable self-contained HTML EDA report.
- Limit chart/category generation so high-cardinality columns do not freeze the application.

### Frontend work

- Build the Profile step.
- Show overview cards, column summary, missing-value summary and duplicate count.
- Show numeric distributions, categorical frequencies and correlation heatmap.
- Add Download EDA Report.

### Automated tests

Backend tests must verify exact known fixture facts:

- Missing-value counts
- Duplicate-row count
- Numeric/categorical detection
- Descriptive-statistic keys
- Valid correlation output
- HTML report response and content type

Frontend component tests must cover loading, success, empty-chart and error states.

Playwright must upload each fixture, open Profile, verify known values and download the HTML report.

### Acceptance criteria

- EDA is derived from the uploaded file, not mocked frontend data.
- Known fixture values match the report.
- The HTML report downloads successfully.
- Tests pass.

---

## Slice 3 — Task, target, feature and preprocessing configuration

### Goal

Let the user create a valid training configuration and preview its effect before training.

### Backend work

- Define validated schemas for task type, target, selected features, missing-value behavior, duplicate removal and scaler.
- Regression/classification require one target.
- Clustering forbids a target.
- All eligible non-target columns are selected by default.
- Support drop-rows-with-missing-values.
- Support duplicate removal.
- Support `none`, `standard` and `minmax` scaling.
- Support one-hot encoding for supervised categorical features.
- Restrict clustering v1 to numeric selected features.
- Return a preprocessing preview: original rows, removed missing rows, removed duplicates, final rows and final feature list.
- Reject leakage such as selecting the target as a feature.

### Frontend work

- Add task selector.
- Show target selector only for regression/classification.
- Add feature include/exclude controls.
- Add missing-value, duplicate and scaling controls.
- Show preprocessing impact before enabling Train.
- Clearly warn when many rows will be removed.

### Automated tests

Backend unit tests must cover:

- Correct target/feature separation
- Target leakage rejection
- Missing-row counts
- Duplicate removal counts
- MinMax and Standard scaling
- One-hot encoding
- Unknown-category handling in later transformed data
- Regression/classification without a target rejection
- Clustering with a target rejection
- Clustering categorical-feature rejection
- Too-few-rows rejection

Playwright must configure:

- `house_prices.csv` for regression with `price_usd` as target
- `customer_segments.csv` for classification with `churned` as target
- `customer_segments.csv` for clustering using numeric features only

### Acceptance criteria

- All three valid configurations reach a ready-to-train state.
- Invalid configurations cannot start training.
- Preprocessing counts are visible and correct.
- Tests pass.

---

## Slice 4 — Regression end-to-end vertical slice

### Goal

Complete the first real ML workflow using regression, including tuning, comparison and basic result charts.

### Backend work

- Create the centralized model registry.
- Register Linear Regression, Random Forest Regressor and XGBoost Regressor.
- Build a reusable preprocessing-and-model pipeline.
- Split data 80/20 using a fixed seed.
- Tune each model using a deliberately small predefined search space and 3-fold cross-validation.
- Ensure tuning uses training data only.
- Evaluate untouched test data using MAE, RMSE and R².
- Select the lowest-RMSE successful model.
- Capture model status, duration, best parameters, metrics and warnings.
- Continue when one model fails.
- Generate actual-versus-predicted, residual and supported feature-importance data.

### Frontend work

- Add training state and progress by model.
- Present a three-model comparison table.
- Highlight the best tested regression model.
- Display best parameters and regression charts.

### Automated tests

- Unit-test metric calculations and lowest-RMSE selection.
- Prove with spies/mocks or controlled data that the test split is not passed into tuning.
- Run a real, bounded training integration test using `house_prices.csv`.
- Assert all three model result records exist.
- Assert successful models contain finite metrics and best parameters.
- Assert the selected winner has the lowest successful RMSE.
- Test graceful partial model failure.
- Playwright uploads `house_prices.csv`, configures regression, starts real training and verifies three model rows, metrics, winner and charts.

### Acceptance criteria

- Regression works end to end from browser upload to real results.
- Hyperparameter tuning genuinely runs for each applicable model.
- UI tests do not replace training results with hard-coded mocks.
- Tests complete within an agreed local test-time budget.

---

## Slice 5 — Classification end-to-end vertical slice

### Goal

Add the complete binary and multiclass-capable classification workflow.

### Backend work

- Register Logistic Regression, Random Forest Classifier and XGBoost Classifier.
- Use stratified 80/20 splitting when possible.
- Tune all three models using bounded search spaces and 3-fold stratified cross-validation.
- Evaluate accuracy, precision, recall and F1 using clearly documented averaging.
- Generate confusion-matrix data and supported feature importance.
- Select the highest-F1 successful model.
- Validate one-class and too-small class targets.

### Frontend work

- Reuse the common training and result components.
- Display classification metrics and confusion matrix.
- Highlight the highest-F1 tested model.
- Show class-distribution information.

### Automated tests

- Unit-test classification metrics and highest-F1 selection.
- Test binary and a small programmatically created multiclass dataset.
- Run real bounded training on `customer_segments.csv`.
- Assert all three result records, finite metrics, best parameters and correct winner.
- Test one-class target rejection.
- Playwright uploads `customer_segments.csv`, configures classification, starts real training and verifies three models, tuning results, confusion matrix and winner.

### Acceptance criteria

- Classification works end to end.
- Both binary and multiclass metric logic is covered.
- Shared regression behavior remains passing.

---

## Slice 6 — Clustering end-to-end vertical slice

### Goal

Add complete unsupervised training and comparison for numeric features.

### Backend work

- Register K-Means, Agglomerative Clustering and DBSCAN.
- Define bounded tuning spaces appropriate to each algorithm.
- Evaluate valid outputs using Silhouette and Davies–Bouldin scores.
- Report cluster count and DBSCAN noise-point count.
- Treat invalid solutions, including one effective cluster or every point marked as noise, as unsuccessful/invalid rather than crashing.
- Select the highest valid Silhouette score.
- Generate two-dimensional PCA projection and cluster-size data.

### Frontend work

- Display clustering comparison results.
- Explain noise points and internal clustering metrics briefly.
- Render PCA cluster visualization and cluster-size chart.
- Highlight the highest valid Silhouette result.

### Automated tests

- Unit-test clustering metrics and invalid-cluster handling.
- Test noise-point counting for DBSCAN.
- Run real bounded clustering on numeric features from `customer_segments.csv` with `churned`, IDs and categorical fields excluded.
- Assert three model result records and at least one valid result.
- Assert winner selection considers only valid results.
- Playwright runs the real clustering flow and verifies model rows, scores, PCA plot and highlighted winner.

### Acceptance criteria

- Clustering works end to end without a target.
- Invalid DBSCAN outcomes are handled clearly.
- All prior workflows continue to pass.

---

## Slice 7 — Artifact export

### Goal

Allow the user to download reusable trained pipelines, graphs, metrics and reports.

### Backend work

- Persist successful experiment artifacts under a generated experiment identifier.
- Export each successful supervised model as a Joblib object containing preprocessing and estimator together.
- Export clustering pipelines with their fitted preprocessing, clustering estimator and metadata required to interpret labels. Document limitations for estimators without general out-of-sample prediction.
- Export `metadata.json`, `metrics.json`, best parameters, graphs and EDA HTML.
- Add a ZIP export for the complete experiment.
- Sanitize filenames and prevent path traversal.
- Return not-found/expired errors cleanly.

### Frontend work

- Add downloads for individual successful models.
- Add Download Best Model.
- Add Download Complete Experiment.
- Disable export for failed models.

### Automated tests

- Download and reload a supervised exported pipeline.
- Use it to predict raw fixture rows without manual preprocessing.
- Confirm metadata identifies task, target, features, preprocessing, model, metrics and timestamp.
- Validate ZIP members and ensure there are no unsafe paths.
- Playwright performs a real regression run, downloads the best model package and complete experiment ZIP, and verifies download completion.

### Acceptance criteria

- A downloaded supervised pipeline can process raw matching rows and predict.
- Graphs, metrics, parameters, metadata and EDA are exportable.
- Export security tests pass.

---

## Slice 8 — Complete UI workflow, resilience and accessibility

### Goal

Polish the demonstration into one coherent, reliable user journey.

### Work

- Finalize five-step navigation and completed/current/disabled states.
- Prevent stale configuration/results when a new CSV is uploaded.
- Add loading, empty, success, warning and error states consistently.
- Prevent accidental duplicate training submissions.
- Make tables and charts usable at common laptop widths.
- Add accessible labels, keyboard navigation, focus handling and status announcements.
- Confirm backend failures appear as friendly UI messages.

### Automated tests

Create a final Playwright suite with these real-data scenarios:

1. Regression using `house_prices.csv`
2. Classification using `customer_segments.csv`
3. Clustering using `customer_segments.csv`
4. Invalid CSV handling
5. Invalid task configuration
6. Replace dataset and confirm stale state is cleared
7. One model fails while other results remain visible
8. Export after successful training

Capture screenshots, traces and videos only on failure to keep normal runs light.

Add an accessibility scan for the principal pages/states and fix serious violations.

### Acceptance criteria

- All three complete browser journeys pass using actual backend training.
- No uncaught browser console errors occur.
- No serious automated accessibility violations remain.
- Backend, frontend and end-to-end suites all pass together.

---

## Slice 9 — Packaging, documentation and final verification

### Goal

Make the project reproducible for college demonstration and handoff.

### Work

- Add a root README with prerequisites, installation, development, test and production commands.
- Add one-command or minimal-command local startup.
- Document supported CSV assumptions and limits.
- Document model lists, metrics, tuning approach and known limitations.
- Document both example CSV workflows.
- Add a short demonstration script/checklist.
- Pin or lock dependencies.
- Add `.env.example` if configuration is necessary; include no secrets.
- Optionally add Docker Compose only if local setup benefits from it; it is not required merely for appearance.

### Final verification

From a clean environment:

1. Install dependencies using only the documented instructions.
2. Start backend and frontend.
3. Run backend tests.
4. Run frontend tests.
5. Install required Playwright browser dependencies.
6. Run the full Playwright suite.
7. Perform the three demonstration workflows.
8. Download and inspect a complete experiment export.

### Acceptance criteria

- A new user can run the project using the README.
- All automated tests pass from a clean setup.
- The demonstration checklist works without undocumented manual fixes.

---

# 6. Testing strategy

## Test layers

| Layer | Purpose | Must not depend on |
|---|---|---|
| Unit | Metrics, validation, preprocessing and selection logic | Browser or running server |
| API integration | Upload, profiling, training and exports | Frontend |
| Frontend component | Rendering and UI state behavior | Expensive real model training |
| Playwright end-to-end | Complete user-visible workflows | Mocked ML success responses |

Component tests may mock API boundaries. At least one Playwright scenario for each task must use the real backend, real preprocessing and real model training.

## Fast tests versus full ML tests

Provide two test modes:

- **Fast suite:** unit/component tests plus small integration checks; used during every slice.
- **Full suite:** includes all real nine-model tuning flows and Playwright; used at slice gates and before delivery.

Test configuration may use smaller bounded tuning grids than demonstration mode, but it must still test more than one parameter configuration for models that have tunable parameters. It must never bypass tuning entirely.

## Non-flakiness rules

- Fix all supported random seeds.
- Use committed fixtures.
- Avoid assertions on exact floating-point model scores unless mathematically stable.
- Assert metric ranges, finiteness, relative winner logic and required shapes.
- Wait for visible application states in Playwright; do not use arbitrary sleep delays.
- Give training operations explicit, reasonable timeouts.
- Preserve Playwright traces on failure.

---

# 7. Definition of done for every slice

A slice is done only when:

- Its functionality is reachable through the intended interface.
- Its acceptance criteria are satisfied.
- New behavior has automated coverage at the correct layer.
- All earlier tests remain passing.
- Formatting, linting and type checking pass.
- No secrets, generated model binaries or temporary uploads are committed.
- Documentation affected by the slice is updated.
- Claude provides a concise completion report and stops before the next slice.

---

# 8. Recommended execution instruction for Claude

Use the following instruction at the beginning of the automated development run:

> Treat `Claude_Implementation_Slices_AutoML_Demo.md` as the controlling implementation plan. Inspect the repository, identify the first incomplete slice, and implement only that slice. Add the specified tests, run both focused and regression tests, fix failures, and verify every acceptance criterion. Do not begin the following slice. At completion, report changed files, implemented behavior, commands and test results, remaining limitations, and the exact next slice awaiting approval.

For a more autonomous run, replace the stopping instruction with:

> Continue through the slices in order. After each slice, run its quality gate and write a checkpoint report before proceeding. If a test cannot pass, a requirement conflicts with the repository, or completing the slice requires changing an approved product decision, stop and report the blocker instead of silently changing scope.

The one-slice-at-a-time mode is recommended because it makes failures easier to locate and prevents Claude from building later functionality on an unverified foundation.
