import path from 'node:path'
import { expect, type Page, test } from '@playwright/test'

const fixturesDir = path.resolve(import.meta.dirname, '../../tests/fixtures')

// Common laptop viewport widths, from the smallest realistic laptop screen
// up to the everyday 1366x768 resolution.
const LAPTOP_VIEWPORTS = [
  { width: 1024, height: 768, label: '1024x768' },
  { width: 1280, height: 800, label: '1280x800' },
  { width: 1366, height: 768, label: '1366x768' },
]

async function expectNoHorizontalOverflow(page: Page, label: string) {
  const overflow = await page.evaluate(() => {
    const doc = document.documentElement
    return { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth }
  })

  expect(
    overflow.scrollWidth,
    `${label}: document.documentElement.scrollWidth (${overflow.scrollWidth}) should not exceed clientWidth (${overflow.clientWidth}) — the page body should never need to scroll horizontally`,
  ).toBeLessThanOrEqual(overflow.clientWidth)
}

for (const viewport of LAPTOP_VIEWPORTS) {
  test(`the full workflow has no horizontal page overflow at ${viewport.label}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })

    await page.goto('/')
    await expectNoHorizontalOverflow(page, `${viewport.label} — Upload (idle)`)

    await page.getByLabel('Upload CSV file').setInputFiles(path.join(fixturesDir, 'house_prices.csv'))
    await page.getByTestId('dataset-summary').waitFor()
    await expectNoHorizontalOverflow(page, `${viewport.label} — Upload (with dataset)`)

    await page.getByRole('button', { name: /continue to profile/i }).click()
    await page.getByRole('heading', { name: 'Dataset profile' }).waitFor()
    await expectNoHorizontalOverflow(page, `${viewport.label} — Profile`)

    await page.getByRole('button', { name: /continue to configure/i }).click()
    await page.getByRole('heading', { name: 'Task' }).waitFor()
    await page.getByLabel('Target column').selectOption('price_usd')
    await page.getByText(/ready to train/i).waitFor()
    await expectNoHorizontalOverflow(page, `${viewport.label} — Configure`)

    // Wide, data-heavy surfaces (the model comparison table, feature-
    // importance bars, scatter charts) are exactly where narrow-viewport
    // overflow is most likely, so exercise the Train results view too —
    // mocked, so three viewports don't mean three real training runs.
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
              status: 'success',
              duration_seconds: 0.15,
              best_params: { model__n_estimators: 200 },
              metrics: { mae: 9500, rmse: 11500, r2: 0.9 },
              warning: null,
              feature_importances: [
                { feature: 'sqft', importance: 0.55 },
                { feature: 'bedrooms', importance: 0.3 },
                { feature: 'bathrooms', importance: 0.15 },
              ],
              charts: {
                actual_vs_predicted: [{ actual: 250000, predicted: 247000 }],
                residuals: [{ predicted: 247000, residual: 3000 }],
              },
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
    await page.getByText('Model comparison').waitFor()
    await expectNoHorizontalOverflow(page, `${viewport.label} — Train (results)`)
  })
}
