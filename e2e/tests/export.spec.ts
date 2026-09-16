import path from 'node:path'
import { expect, test } from '@playwright/test'

const fixturesDir = path.resolve(import.meta.dirname, '../../tests/fixtures')

test('after a real regression run, the best model and the complete experiment both download successfully', async ({
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

  await expect(page.getByText('Model comparison')).toBeVisible({ timeout: 30_000 })

  const experimentDownloadPromise = page.waitForEvent('download')
  await page.getByRole('link', { name: /download complete experiment/i }).click()
  const experimentDownload = await experimentDownloadPromise
  expect(experimentDownload.suggestedFilename()).toMatch(/^experiment_[a-f0-9]{32}\.zip$/)
  expect(await experimentDownload.failure()).toBeNull()

  const bestModelDownloadPromise = page.waitForEvent('download')
  await page.getByRole('link', { name: /download best model/i }).click()
  const bestModelDownload = await bestModelDownloadPromise
  expect(bestModelDownload.suggestedFilename()).toMatch(/\.joblib$/)
  expect(await bestModelDownload.failure()).toBeNull()

  // A successful model's row also offers its own download; a failed one
  // would not (verified directly against the real backend, not mocked).
  const successRows = page.locator('table tbody tr', { hasText: 'Success' })
  await expect(successRows.first().getByRole('link', { name: /^download /i })).toBeVisible()
})
