import { test as adminTest, memberTest, expect } from '../fixtures/index.js'

// /settings/general hosts the Danger Zone (delete organisation). The Owner role
// (Alice / admin@example.org) must see it; non-owners must not.

adminTest.describe('General settings - owner (Alice)', () => {
  adminTest.beforeEach(async ({ page }) => {
    await page.goto('/settings/general')
    await page.waitForURL('/settings/general', { timeout: 10_000 })
  })

  adminTest('Danger Zone card and Delete Organization button are visible', async ({ page }) => {
    await expect(page.getByText(/danger zone/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /delete organization/i })).toBeVisible()
  })

  adminTest('clicking delete opens a confirmation alertdialog', async ({ page }) => {
    await page.getByRole('button', { name: /delete organization/i }).click()
    await expect(page.getByRole('alertdialog')).toBeVisible()
  })

  adminTest('cancelling the confirm dialog closes it without navigating', async ({ page }) => {
    await page.getByRole('button', { name: /delete organization/i }).click()
    await expect(page.getByRole('alertdialog')).toBeVisible()
    await page
      .getByRole('alertdialog')
      .getByRole('button', { name: /cancel/i })
      .click()
    await expect(page.getByRole('alertdialog')).not.toBeVisible()
    await expect(page).toHaveURL('/settings/general')
  })

  adminTest(
    'confirming delete calls DELETE API, logs out, and redirects to /login',
    async ({ page }) => {
      // Stub both the delete and logout endpoints so the seed org is never touched
      // and the auth cookie is not actually cleared (which would break subsequent tests).
      await page.route('**/v1/organizations/**', (route) => {
        if (route.request().method() === 'DELETE') {
          route.fulfill({ status: 204, body: '' })
        } else {
          route.continue()
        }
      })
      await page.route('**/v1/auth/logout', (route) =>
        route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
      )

      await page.getByRole('button', { name: /delete organization/i }).click()
      await expect(page.getByRole('alertdialog')).toBeVisible()

      const confirmBtn = page.getByRole('alertdialog').getByRole('button', { name: /delete/i })
      await confirmBtn.click()

      await page.waitForURL('/login', { timeout: 10_000 })
      await expect(page).toHaveURL('/login')
    },
  )
})

memberTest.describe('General settings - member (Bob)', () => {
  memberTest('Danger Zone is not visible for non-Owner role', async ({ page }) => {
    await page.goto('/settings/general')
    await page.waitForURL('/settings/general', { timeout: 10_000 })
    await expect(page.getByText(/danger zone/i)).not.toBeVisible()
    await expect(page.getByRole('button', { name: /delete organization/i })).not.toBeVisible()
  })
})
