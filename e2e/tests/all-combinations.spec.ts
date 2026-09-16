import path from 'node:path'
import { expect, type Page, test } from '@playwright/test'

const fixturesDir = path.resolve(import.meta.dirname, '../../tests/fixtures')

// Every column, in file order, for both committed fixtures — including the
// identifier-like column (property_id / customer_id) and every numeric
// column that's clearly *not* meant to be a category, so this suite covers
// the deliberately "wrong" choices a real user might click, not just the
// two intended target columns already covered by configure.spec.ts /
// train.spec.ts.
const HOUSE_PRICES = {
  file: 'house_prices.csv',
  columns: [
    'property_id',
    'area_m2',
    'bedrooms',
    'age_years',
    'distance_to_center_km',
    'neighborhood',
    'has_parking',
    'price_usd',
  ],
}

const CUSTOMER_SEGMENTS = {
  file: 'customer_segments.csv',
  columns: [
    'customer_id',
    'age',
    'annual_income',
    'spending_score',
    'visits_per_month',
    'membership_type',
    'region',
    'churned',
  ],
}

// A generous but finite bound: this suite's entire point is proving no
// combination ever produces the kind of hundreds-of-values wall of text
// the real bug did, for any column in either fixture.
const MAX_WARNING_LENGTH = 400

function isPreviewResponse(response: { url: () => string; request: () => { method(): string } }) {
  return response.url().includes('/preprocessing-preview') && response.request().method() === 'POST'
}

/**
 * Runs `action` (a target-select or task-radio click) and waits for the
 * *network response* it triggers before reading the resulting UI state.
 * Waiting on transient text like "Computing preprocessing impact…" is
 * inherently racy — Playwright's polling can observe 0 matches either
 * because the request hasn't started yet or because it already finished,
 * and those two cases are indistinguishable from text alone. Tying the wait
 * to the actual debounced POST /preprocessing-preview response removes that
 * ambiguity: by the time this resolves, the specific request `action`
 * caused has genuinely completed, so the DOM (checked right after, with
 * Playwright's normal auto-retrying assertions) reflects that exact change,
 * not a stale one from the previous combination.
 */
async function settlePreviewAfter(
  page: Page,
  action: () => Promise<void>,
): Promise<'ready' | 'not-ready' | 'incomplete'> {
  const [response] = await Promise.all([
    page.waitForResponse(isPreviewResponse, { timeout: 10_000 }),
    action(),
  ])
  expect(response.ok(), `preprocessing-preview request failed: ${response.status()}`).toBe(true)

  const readyBadge = page.getByText('Ready to train', { exact: true })
  const notReadyBadge = page.getByText('Not ready', { exact: true })
  const incomplete = page.getByText(
    'Complete the configuration above to see the preprocessing impact.',
  )

  await expect(readyBadge.or(notReadyBadge).or(incomplete)).toBeVisible({ timeout: 10_000 })

  if (await readyBadge.isVisible()) return 'ready'
  if (await notReadyBadge.isVisible()) return 'not-ready'
  return 'incomplete'
}

async function assertWarningsAreBounded(page: Page) {
  const warnings = await page.getByTestId('config-warning').allTextContents()
  for (const warning of warnings) {
    expect(
      warning.length,
      `a Configure warning must stay a short, readable sentence, not a wall of raw values: "${warning.slice(0, 120)}…"`,
    ).toBeLessThan(MAX_WARNING_LENGTH)
  }
}

/**
 * Walks Task × Target for every column in one fixture, all within a single
 * page session (no reload per combination — just driving the same radio
 * group / dropdown repeatedly, exactly like a user clicking through options)
 * so the whole matrix runs in one pass. For every combination the app must
 * settle into a clean, bounded state — either genuinely ready to train, or
 * clearly "not ready" with short, readable warnings — and must never throw
 * an uncaught error in the browser, regardless of how nonsensical the
 * chosen target is for the chosen task.
 */
async function walkAllTaskTargetCombinations(page: Page, dataset: { file: string; columns: string[] }) {
  const pageErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))

  await page.goto('/')
  await page.getByLabel('Upload CSV file').setInputFiles(path.join(fixturesDir, dataset.file))
  await page.getByRole('button', { name: /continue to profile/i }).click()
  await page.getByRole('button', { name: /continue to configure/i }).click()
  await page.getByRole('heading', { name: 'Task' }).waitFor()

  const results: { task: string; target: string | null; state: string }[] = []

  for (const task of ['regression', 'classification'] as const) {
    // Not wrapped in settlePreviewAfter: on the very first iteration no
    // target has been chosen yet, so this click may not trigger a
    // preprocessing-preview request at all (an incomplete config never
    // calls the API) — there would be nothing to wait for.
    await page.getByRole('radio', { name: new RegExp(task, 'i') }).click()

    for (const column of dataset.columns) {
      const state = await settlePreviewAfter(page, () =>
        page.getByLabel('Target column').selectOption(column),
      )
      await assertWarningsAreBounded(page)
      results.push({ task, target: column, state })
    }
  }

  // Clustering has no target column at all — just walk it once. By this
  // point a target is already set from the classification loop above, so
  // switching to clustering always changes the config and fires a request.
  const clusteringState = await settlePreviewAfter(page, () =>
    page.getByRole('radio', { name: /clustering/i }).click(),
  )
  await assertWarningsAreBounded(page)
  results.push({ task: 'clustering', target: null, state: clusteringState })

  expect(pageErrors, `uncaught browser error(s) while walking ${dataset.file}: ${pageErrors.join('; ')}`).toEqual([])

  return results
}

test('every task × target combination on house_prices.csv settles cleanly, with the real regression target reaching ready-to-train', async ({
  page,
}) => {
  test.setTimeout(60_000)

  const results = await walkAllTaskTargetCombinations(page, HOUSE_PRICES)

  const regressionOnPrice = results.find((r) => r.task === 'regression' && r.target === 'price_usd')
  expect(regressionOnPrice?.state).toBe('ready')

  // The near-unique identifier column and the continuous distance column are
  // exactly the "wrong click" cases the real bug came from — neither should
  // ever reach "ready" as a classification target.
  const classificationOnId = results.find(
    (r) => r.task === 'classification' && r.target === 'property_id',
  )
  const classificationOnDistance = results.find(
    (r) => r.task === 'classification' && r.target === 'distance_to_center_km',
  )
  expect(classificationOnId?.state).toBe('not-ready')
  expect(classificationOnDistance?.state).toBe('not-ready')

  // The regression-side counterpart of the same bug family: a categorical
  // column (a neighborhood name, a yes/no flag) picked as a *regression*
  // target used to reach GridSearchCV and fail deep inside sklearn with a
  // raw "could not convert string to float" traceback shown to the user.
  const regressionOnNeighborhood = results.find(
    (r) => r.task === 'regression' && r.target === 'neighborhood',
  )
  const regressionOnHasParking = results.find(
    (r) => r.task === 'regression' && r.target === 'has_parking',
  )
  expect(regressionOnNeighborhood?.state).toBe('not-ready')
  expect(regressionOnHasParking?.state).toBe('not-ready')

  const clustering = results.find((r) => r.task === 'clustering')
  expect(clustering?.state).not.toBe('incomplete')
})

test('every task × target combination on customer_segments.csv settles cleanly, with the real classification target reaching ready-to-train', async ({
  page,
}) => {
  test.setTimeout(60_000)

  const results = await walkAllTaskTargetCombinations(page, CUSTOMER_SEGMENTS)

  const classificationOnChurned = results.find(
    (r) => r.task === 'classification' && r.target === 'churned',
  )
  expect(classificationOnChurned?.state).toBe('ready')

  const classificationOnIncome = results.find(
    (r) => r.task === 'classification' && r.target === 'annual_income',
  )
  expect(classificationOnIncome?.state).toBe('not-ready')

  // Regression-side counterpart: a categorical target must not reach ready.
  const regressionOnMembership = results.find(
    (r) => r.task === 'regression' && r.target === 'membership_type',
  )
  expect(regressionOnMembership?.state).toBe('not-ready')

  const clustering = results.find((r) => r.task === 'clustering')
  expect(clustering?.state).not.toBe('incomplete')
})
