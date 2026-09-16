import path from 'node:path'
import { expect, type Page } from '@playwright/test'
import { test } from '@playwright/test'

const fixturesDir = path.resolve(import.meta.dirname, '../../tests/fixtures')

async function uploadAndReachConfigure(page: Page, fixture: string) {
  await page.goto('/')
  await page.getByLabel('Upload CSV file').setInputFiles(path.join(fixturesDir, fixture))
  await page.getByRole('button', { name: /continue to profile/i }).click()
  await page.getByRole('button', { name: /continue to configure/i }).click()
  await expect(page.getByRole('heading', { name: 'Task' })).toBeVisible()
}

test('configuring regression on house_prices.csv reaches a ready-to-train state', async ({ page }) => {
  await uploadAndReachConfigure(page, 'house_prices.csv')

  // Regression is the default task.
  await expect(page.getByRole('radio', { name: /regression/i })).toHaveAttribute('aria-checked', 'true')

  await page.getByLabel('Target column').selectOption('price_usd')

  await expect(page.getByText(/ready to train/i)).toBeVisible()
  await expect(page.getByText('Original rows').locator('..')).toContainText('222')
  await expect(page.getByText('Final rows').locator('..')).toContainText('214')
})

test('configuring classification on customer_segments.csv reaches a ready-to-train state', async ({
  page,
}) => {
  await uploadAndReachConfigure(page, 'customer_segments.csv')

  await page.getByRole('radio', { name: /classification/i }).click()
  await page.getByLabel('Target column').selectOption('churned')

  await expect(page.getByText(/ready to train/i)).toBeVisible()
  await expect(page.getByText('Final rows').locator('..')).toContainText('214')
})

test('configuring clustering on customer_segments.csv uses numeric features only and reaches a ready-to-train state', async ({
  page,
}) => {
  await uploadAndReachConfigure(page, 'customer_segments.csv')

  await page.getByRole('radio', { name: /clustering/i }).click()

  await expect(page.getByLabel('Target column')).toHaveCount(0)

  const regionRow = page.getByText('region', { exact: true }).locator('..')
  await expect(regionRow.locator('input[type="checkbox"]')).toBeDisabled()

  await expect(page.getByText(/ready to train/i)).toBeVisible()
  await expect(page.getByText('Final rows').locator('..')).toContainText('216')
})

test('an incomplete task configuration (no target selected) blocks training and shows "not ready"', async ({
  page,
}) => {
  await uploadAndReachConfigure(page, 'house_prices.csv')

  // Regression is the default task, and no target is selected yet.
  await expect(page.getByLabel('Target column')).toHaveValue('')
  await expect(
    page.getByText('Complete the configuration above to see the preprocessing impact.'),
  ).toBeVisible()
  await expect(page.getByText(/ready to train/i)).toHaveCount(0)
  await expect(page.getByRole('button', { name: /continue to train/i })).toBeDisabled()

  // Selecting a target completes the configuration and unblocks training.
  await page.getByLabel('Target column').selectOption('price_usd')
  await expect(page.getByText(/ready to train/i)).toBeVisible()
  await expect(page.getByRole('button', { name: /continue to train/i })).toBeEnabled()

  // Unchecking every feature makes the configuration incomplete again, even
  // with a target selected.
  const featureCheckboxes = page.locator('input[type="checkbox"]')
  const count = await featureCheckboxes.count()
  for (let i = 0; i < count; i++) {
    await featureCheckboxes.nth(i).uncheck({ force: true })
  }

  await expect(
    page.getByText('Complete the configuration above to see the preprocessing impact.'),
  ).toBeVisible()
  await expect(page.getByRole('button', { name: /continue to train/i })).toBeDisabled()
})
