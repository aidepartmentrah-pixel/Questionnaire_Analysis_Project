import path from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, type Page, test } from '@playwright/test'

const fixturesDir = path.resolve(import.meta.dirname, '../../tests/fixtures')

const SERIOUS_IMPACTS = ['serious', 'critical']

async function expectNoSeriousViolations(page: Page, label: string) {
  const results = await new AxeBuilder({ page }).analyze()
  const serious = results.violations.filter((v) => SERIOUS_IMPACTS.includes(v.impact ?? ''))

  if (serious.length > 0) {
    const summary = serious
      .map((v) => `${v.id} (${v.impact}): ${v.help} — ${v.nodes.length} node(s)`)
      .join('\n')
    throw new Error(`Serious accessibility violations on ${label}:\n${summary}`)
  }
}

test('the Upload step (idle) has no serious accessibility violations', async ({ page }) => {
  await page.goto('/')
  await expectNoSeriousViolations(page, 'Upload (idle)')
})

test('the Upload step (with a dataset loaded) has no serious accessibility violations', async ({
  page,
}) => {
  await page.goto('/')
  await page.getByLabel('Upload CSV file').setInputFiles(path.join(fixturesDir, 'house_prices.csv'))
  await page.getByText('house_prices.csv').waitFor()
  await expectNoSeriousViolations(page, 'Upload (success)')
})

test('the Profile step has no serious accessibility violations', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Upload CSV file').setInputFiles(path.join(fixturesDir, 'house_prices.csv'))
  await page.getByRole('button', { name: /continue to profile/i }).click()
  await page.getByRole('heading', { name: 'Dataset profile' }).waitFor()
  await expectNoSeriousViolations(page, 'Profile')
})

test('the Configure step has no serious accessibility violations', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Upload CSV file').setInputFiles(path.join(fixturesDir, 'house_prices.csv'))
  await page.getByRole('button', { name: /continue to profile/i }).click()
  await page.getByRole('button', { name: /continue to configure/i }).click()
  await page.getByRole('heading', { name: 'Task' }).waitFor()
  await expectNoSeriousViolations(page, 'Configure')
})

test('the Train step results view has no serious accessibility violations', async ({ page }) => {
  test.setTimeout(60_000)

  await page.goto('/')
  await page.getByLabel('Upload CSV file').setInputFiles(path.join(fixturesDir, 'house_prices.csv'))
  await page.getByRole('button', { name: /continue to profile/i }).click()
  await page.getByRole('button', { name: /continue to configure/i }).click()
  await page.getByLabel('Target column').selectOption('price_usd')
  await page.getByText(/ready to train/i).waitFor()
  await page.getByRole('button', { name: /continue to train/i }).click()
  await page.getByRole('button', { name: /start training/i }).click()
  await page.getByText('Model comparison').waitFor({ timeout: 30_000 })

  await expectNoSeriousViolations(page, 'Train (results)')
})
