import path from 'node:path'
import { expect, test } from '@playwright/test'

const fixturesDir = path.resolve(import.meta.dirname, '../../tests/fixtures')

test('profiling customer_segments.csv shows known facts and downloads the EDA report', async ({
  page,
}) => {
  await page.goto('/')

  const fileInput = page.getByLabel('Upload CSV file')
  await fileInput.setInputFiles(path.join(fixturesDir, 'customer_segments.csv'))
  await page.getByRole('button', { name: /continue to profile/i }).click()

  await expect(page.getByRole('heading', { name: 'Dataset profile' })).toBeVisible()
  await expect(page.getByText('customer_segments.csv')).toBeVisible()

  const rowsCard = page.getByText('Rows', { exact: true }).locator('..')
  await expect(rowsCard).toContainText('222')

  const duplicatesCard = page.getByText('Duplicate rows', { exact: true }).locator('..')
  await expect(duplicatesCard).toContainText('2')

  const columnsTable = page.getByRole('table').first()
  await expect(columnsTable).toContainText('membership_type')
  await expect(columnsTable).toContainText('categorical')

  await expect(page.getByRole('heading', { name: 'Numeric distributions' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Categorical frequencies' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Correlation matrix' })).toBeVisible()

  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('link', { name: /download eda report/i }).click()
  const download = await downloadPromise

  expect(download.suggestedFilename()).toMatch(/eda_report_.*\.html$/)
})

test('profiling house_prices.csv shows known facts', async ({ page }) => {
  await page.goto('/')

  const fileInput = page.getByLabel('Upload CSV file')
  await fileInput.setInputFiles(path.join(fixturesDir, 'house_prices.csv'))
  await page.getByRole('button', { name: /continue to profile/i }).click()

  await expect(page.getByRole('heading', { name: 'Dataset profile' })).toBeVisible()
  await expect(page.getByText('house_prices.csv')).toBeVisible()

  const rowsCard = page.getByText('Rows', { exact: true }).locator('..')
  await expect(rowsCard).toContainText('222')

  const columnsTable = page.getByRole('table').first()
  await expect(columnsTable).toContainText('neighborhood')
  await expect(columnsTable).toContainText('price_usd')

  await expect(page.getByRole('heading', { name: 'Correlation matrix' })).toBeVisible()
})
