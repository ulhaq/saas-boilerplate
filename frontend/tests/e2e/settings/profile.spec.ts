import { test, expect } from '../fixtures/index.js'

test.describe('Profile settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForURL('/settings', { timeout: 10_000 })
  })

  test('profile page loads with current user name and email prefilled', async ({ page }) => {
    // Admin user is Alice Owner with email admin@example.org
    await expect(page.locator('input').first()).toHaveValue(/Alice/)
    await expect(page.locator('input').last()).toHaveValue('admin@example.org')
  })

  test('clearing name shows validation error on save', async ({ page }) => {
    const nameInput = page.locator('input').first()
    await nameInput.clear()
    await page.getByRole('button', { name: 'Save changes' }).click()
    await expect(page.locator('.text-destructive').first()).toBeVisible()
  })

  test('successful profile update shows success toast', async ({ page }) => {
    const nameInput = page.locator('input').first()
    await nameInput.clear()
    await nameInput.fill('Alice Owner Updated')
    await page.getByRole('button', { name: 'Save changes' }).click()
    await expect(page.getByRole('list').getByText('Profile updated')).toBeVisible({ timeout: 5000 })

    // Restore original name
    await nameInput.clear()
    await nameInput.fill('Alice Owner')
    await page.getByRole('button', { name: 'Save changes' }).click()
  })
})
