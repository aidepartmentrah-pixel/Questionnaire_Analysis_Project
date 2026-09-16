import { expect, test } from '@playwright/test'

test('the app loads, shows its title and the five-step workflow', async ({ page }) => {
  await page.goto('/')

  await expect(page).toHaveTitle('AutoML Studio')
  await expect(page.getByRole('heading', { name: 'AutoML Studio' })).toBeVisible()

  for (const label of ['Upload', 'Profile', 'Configure', 'Train', 'Results']) {
    await expect(page.getByText(label, { exact: true })).toBeVisible()
  }

  await expect(page.getByText(/backend connected/i)).toBeVisible()
})
