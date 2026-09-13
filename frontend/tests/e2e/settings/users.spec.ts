import { test, expect } from '../fixtures/index.js'

test.describe('Users settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings/users')
    await page.waitForURL('/settings/users', { timeout: 10_000 })
  })

  test('users list loads and shows seeded users', async ({ page }) => {
    const table = page.locator('table')
    await expect(table.getByText('Alice Owner')).toBeVisible()
    await expect(table.getByText('Bob Member')).toBeVisible()
  })

  test('Invite user button is visible for admin', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Invite user' })).toBeVisible()
  })

  test('invite dialog opens and shows email field', async ({ page }) => {
    await page.getByRole('button', { name: 'Invite user' }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByRole('dialog').locator('#email, input[type="text"]')).toBeVisible()
  })

  test('invite dialog: submitting valid email shows success state', async ({ page }) => {
    await page.getByRole('button', { name: 'Invite user' }).click()
    const dialog = page.getByRole('dialog')
    const emailInput = dialog
      .locator('input[type="text"], input[placeholder*="email"], input[placeholder*="john"]')
      .first()
    await emailInput.fill(`e2e-invite-${Date.now()}@test.com`)
    await dialog.getByRole('button', { name: 'Send invitation' }).click()
    await expect(page.getByRole('list').getByText('Invitation sent')).toBeVisible({ timeout: 5000 })
  })

  test('search filters the user list', async ({ page }) => {
    await page.locator('input[placeholder*="Search"]').fill('Alice')
    await page.waitForTimeout(400)
    await expect(page.locator('table').getByText('Alice Owner').first()).toBeVisible()
    await expect(page.getByText('Bob Member')).not.toBeVisible()
  })

  test('clearing search restores full list', async ({ page }) => {
    await page.locator('input[placeholder*="Search"]').fill('Alice')
    await page.waitForTimeout(400)
    await page.locator('input[placeholder*="Search"] + button').click()
    await page.waitForTimeout(400)
    await expect(page.getByText('Bob Member')).toBeVisible()
  })
})
