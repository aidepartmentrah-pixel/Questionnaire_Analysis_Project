import path from 'node:path'
import { expect, test } from '@playwright/test'

const fixturesDir = path.resolve(import.meta.dirname, '../../tests/fixtures')

test('uploading a CSV shows its structure, and uploading another replaces it', async ({ page }) => {
  await page.goto('/')

  const fileInput = page.getByLabel('Upload CSV file')
  const summary = page.getByTestId('dataset-summary')
  const table = page.getByRole('table')

  await fileInput.setInputFiles(path.join(fixturesDir, 'customer_segments.csv'))

  await expect(summary).toContainText('customer_segments.csv')
  await expect(summary).toContainText('222')
  await expect(summary).toContainText('8 columns')

  await expect(table).toContainText('customer_id')
  await expect(table).toContainText('churned')
  await expect(page.locator('table tbody tr').first()).toBeVisible()

  await fileInput.setInputFiles(path.join(fixturesDir, 'house_prices.csv'))

  await expect(summary).toContainText('house_prices.csv')
  await expect(summary).toContainText('222')
  await expect(summary).toContainText('8 columns')

  await expect(table).toContainText('property_id')
  await expect(table).toContainText('price_usd')
  await expect(page.getByText('customer_segments.csv')).toHaveCount(0)
  await expect(table).not.toContainText('customer_id')
})

test('replacing the dataset after configuring it clears the stale target, features and readiness state', async ({
  page,
}) => {
  await page.goto('/')

  await page.getByLabel('Upload CSV file').setInputFiles(path.join(fixturesDir, 'house_prices.csv'))
  await page.getByRole('button', { name: /continue to profile/i }).click()
  await page.getByRole('button', { name: /continue to configure/i }).click()

  await page.getByLabel('Target column').selectOption('price_usd')
  await expect(page.getByText(/ready to train/i)).toBeVisible()
  await expect(page.getByRole('button', { name: /continue to train/i })).toBeEnabled()

  // Navigate back to Upload via the step nav (completed steps are
  // clickable) and replace the active dataset with a different one.
  await page.getByRole('button', { name: /go back to upload/i }).click()
  await page.getByLabel('Upload CSV file').setInputFiles(path.join(fixturesDir, 'customer_segments.csv'))
  await expect(page.getByTestId('dataset-summary')).toContainText('customer_segments.csv')

  await page.getByRole('button', { name: /continue to profile/i }).click()
  await page.getByRole('button', { name: /continue to configure/i }).click()

  // The Configure step must have remounted fresh for the new dataset: no
  // leftover target selection, no stale "ready to train" preview, and the
  // target dropdown reflects the new dataset's columns rather than the old
  // one's (house_prices' price_usd must be gone; customer_segments' churned
  // must be present).
  await expect(page.getByLabel('Target column')).toHaveValue('')
  await expect(page.getByLabel('Target column').locator('option', { hasText: 'price_usd' })).toHaveCount(0)
  await expect(page.getByLabel('Target column').locator('option', { hasText: 'churned' })).toHaveCount(1)
  await expect(
    page.getByText('Complete the configuration above to see the preprocessing impact.'),
  ).toBeVisible()
  await expect(page.getByText(/ready to train/i)).toHaveCount(0)
  await expect(page.getByRole('button', { name: /continue to train/i })).toBeDisabled()
})

test('an invalid file shows a friendly validation error', async ({ page }) => {
  await page.goto('/')

  const fileInput = page.getByLabel('Upload CSV file')
  await fileInput.setInputFiles({
    name: 'empty.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(''),
  })

  const alert = page.getByRole('alert')
  await expect(alert).toBeVisible()
  await expect(alert).toContainText(/empty/i)
})
