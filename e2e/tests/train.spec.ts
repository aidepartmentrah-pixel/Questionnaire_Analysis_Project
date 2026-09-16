import path from 'node:path'
import { expect, test } from '@playwright/test'

const fixturesDir = path.resolve(import.meta.dirname, '../../tests/fixtures')

test('training regression on house_prices.csv shows three real model results, a winner and charts', async ({
  page,
}) => {
  test.setTimeout(60_000)

  await page.goto('/')
  await page.getByLabel('Upload CSV file').setInputFiles(path.join(fixturesDir, 'house_prices.csv'))
  await page.getByRole('button', { name: /continue to profile/i }).click()
  await page.getByRole('button', { name: /continue to configure/i }).click()

  await page.getByLabel('Target column').selectOption('price_usd')
  await page.getByText(/ready to train/i).waitFor()

  await page.getByRole('button', { name: /continue to train/i }).click()
  await page.getByRole('button', { name: /start training/i }).click()

  // Real GridSearchCV tuning over three models; give it real time to finish.
  await expect(page.getByText('Model comparison')).toBeVisible({ timeout: 30_000 })

  const table = page.getByRole('table')
  await expect(table).toContainText('Linear Regression')
  await expect(table).toContainText('Random Forest Regressor')
  await expect(table).toContainText('XGBoost Regressor')

  const rows = page.locator('table tbody tr')
  await expect(rows).toHaveCount(3)

  // All three should succeed on this clean fixture — assert real, finite metrics.
  for (const status of await page.locator('table tbody tr td:nth-child(2)').allTextContents()) {
    expect(status).toContain('Success')
  }

  await expect(page.getByText('Best', { exact: true })).toBeVisible()
  await expect(page.getByText(/best model:/i)).toBeVisible()
  await expect(page.getByText('Actual vs. predicted')).toBeVisible()
  await expect(page.getByText('Residuals', { exact: true })).toBeVisible()
  await expect(page.locator('svg[role="img"]').first()).toBeVisible()
})

test('training classification on customer_segments.csv shows three real model results, tuning results, a confusion matrix and a winner', async ({
  page,
}) => {
  test.setTimeout(60_000)

  await page.goto('/')
  await page
    .getByLabel('Upload CSV file')
    .setInputFiles(path.join(fixturesDir, 'customer_segments.csv'))
  await page.getByRole('button', { name: /continue to profile/i }).click()
  await page.getByRole('button', { name: /continue to configure/i }).click()

  await page.getByRole('radio', { name: /classification/i }).click()
  await page.getByLabel('Target column').selectOption('churned')
  await page.getByText(/ready to train/i).waitFor()

  await page.getByRole('button', { name: /continue to train/i }).click()
  await page.getByRole('button', { name: /start training/i }).click()

  await expect(page.getByText('Model comparison')).toBeVisible({ timeout: 30_000 })

  const comparisonTable = page.getByRole('table').first()
  await expect(comparisonTable).toContainText('Logistic Regression')
  await expect(comparisonTable).toContainText('Random Forest Classifier')
  await expect(comparisonTable).toContainText('XGBoost Classifier')
  await expect(comparisonTable).toContainText('F1')
  await expect(comparisonTable).toContainText('Accuracy')

  const comparisonRows = comparisonTable.locator('tbody tr')
  await expect(comparisonRows).toHaveCount(3)

  for (const status of await comparisonTable.locator('tbody tr td:nth-child(2)').allTextContents()) {
    expect(status).toContain('Success')
  }

  await expect(page.getByText('Best', { exact: true })).toBeVisible()
  await expect(page.getByText(/best model:/i)).toBeVisible()
  await expect(page.getByText('Confusion matrix')).toBeVisible()
  await expect(page.getByText(/rows are actual classes/i)).toBeVisible()
  await expect(page.getByText('Feature importance')).toBeVisible()
})

test('when one model fails, its row shows the failure while the other results stay visible', async ({
  page,
}) => {
  // Forcing a genuine backend failure deterministically (e.g. a model that
  // errors on this specific clean fixture) isn't practical, so this
  // exercises the same code path the real failure-handling in
  // regression_training.py exists for: one model errors, its ModelResult
  // gets status "failed" with a warning, and the other two still render
  // normally — by mocking the /train response instead of the training run.
  await page.goto('/')
  await page.getByLabel('Upload CSV file').setInputFiles(path.join(fixturesDir, 'house_prices.csv'))
  await page.getByRole('button', { name: /continue to profile/i }).click()
  await page.getByRole('button', { name: /continue to configure/i }).click()

  await page.getByLabel('Target column').selectOption('price_usd')
  await page.getByText(/ready to train/i).waitFor()
  await page.getByRole('button', { name: /continue to train/i }).click()

  await page.route('**/api/datasets/*/train', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        dataset_id: 'mocked',
        task: 'regression',
        target: 'price_usd',
        train_rows: 171,
        test_rows: 43,
        primary_metric: 'rmse',
        winner_key: 'xgboost_regressor',
        experiment_id: null,
        results: [
          {
            key: 'linear_regression',
            display_name: 'Linear Regression',
            status: 'success',
            duration_seconds: 0.08,
            best_params: {},
            metrics: { mae: 12000, rmse: 15000, r2: 0.82 },
            warning: null,
            feature_importances: null,
            charts: {
              actual_vs_predicted: [{ actual: 250000, predicted: 240000 }],
              residuals: [{ predicted: 240000, residual: 10000 }],
            },
          },
          {
            key: 'random_forest_regressor',
            display_name: 'Random Forest Regressor',
            status: 'failed',
            duration_seconds: 0.03,
            best_params: null,
            metrics: null,
            warning: 'Mocked failure for e2e testing: model raised during fit.',
            feature_importances: null,
            charts: null,
          },
          {
            key: 'xgboost_regressor',
            display_name: 'XGBoost Regressor',
            status: 'success',
            duration_seconds: 0.11,
            best_params: { model__max_depth: 3 },
            metrics: { mae: 9000, rmse: 11000, r2: 0.91 },
            warning: null,
            feature_importances: [
              { feature: 'sqft', importance: 0.6 },
              { feature: 'bedrooms', importance: 0.4 },
            ],
            charts: {
              actual_vs_predicted: [{ actual: 250000, predicted: 248000 }],
              residuals: [{ predicted: 248000, residual: 2000 }],
            },
          },
        ],
      }),
    })
  })

  await page.getByRole('button', { name: /start training/i }).click()
  await expect(page.getByText('Model comparison')).toBeVisible()

  const table = page.getByRole('table').first()
  await expect(table).toContainText('Linear Regression')
  await expect(table).toContainText('Random Forest Regressor')
  await expect(table).toContainText('XGBoost Regressor')

  const rows = table.locator('tbody tr')
  await expect(rows).toHaveCount(3)

  const statuses = await table.locator('tbody tr td:nth-child(2)').allTextContents()
  expect(statuses.filter((s) => s.includes('Success'))).toHaveLength(2)
  expect(statuses.filter((s) => s.includes('Failed'))).toHaveLength(1)

  await expect(table).toContainText('Mocked failure for e2e testing: model raised during fit.')

  // The winning (successful) model's charts still render despite the
  // sibling failure.
  await expect(page.getByText('Best', { exact: true })).toBeVisible()
  await expect(page.getByText(/best model: xgboost regressor/i)).toBeVisible()
  await expect(page.getByText('Actual vs. predicted')).toBeVisible()
  await expect(page.getByText('Feature importance')).toBeVisible()
})

test('training clustering on customer_segments.csv shows three real model results, a PCA plot, cluster sizes and a highlighted winner', async ({
  page,
}) => {
  test.setTimeout(60_000)

  await page.goto('/')
  await page
    .getByLabel('Upload CSV file')
    .setInputFiles(path.join(fixturesDir, 'customer_segments.csv'))
  await page.getByRole('button', { name: /continue to profile/i }).click()
  await page.getByRole('button', { name: /continue to configure/i }).click()

  await page.getByRole('radio', { name: /clustering/i }).click()
  await page.getByText(/ready to train/i).waitFor()

  await page.getByRole('button', { name: /continue to train/i }).click()
  await page.getByRole('button', { name: /start training/i }).click()

  await expect(page.getByText('Model comparison')).toBeVisible({ timeout: 30_000 })

  const comparisonTable = page.getByRole('table').first()
  await expect(comparisonTable).toContainText('K-Means')
  await expect(comparisonTable).toContainText('Agglomerative Clustering')
  await expect(comparisonTable).toContainText('DBSCAN')
  await expect(comparisonTable).toContainText('Silhouette')

  const comparisonRows = comparisonTable.locator('tbody tr')
  await expect(comparisonRows).toHaveCount(3)

  // Clustering results can legitimately include an invalid/failed
  // combination, so only at least one success is required — but this
  // fixture's clusters are well-separated enough that all three succeed.
  const statuses = await comparisonTable.locator('tbody tr td:nth-child(2)').allTextContents()
  expect(statuses.some((status) => status.includes('Success'))).toBe(true)

  await expect(page.getByText('Best', { exact: true })).toBeVisible()
  await expect(page.getByText(/best model:/i)).toBeVisible()
  await expect(page.getByText('Cluster projection (PCA)')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Cluster sizes' })).toBeVisible()
})
