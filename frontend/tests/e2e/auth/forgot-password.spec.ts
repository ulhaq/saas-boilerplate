import { test, expect } from '@playwright/test'

test.describe('Forgot password page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/forgot-password')
  })

  test('renders forgot-password form', async ({ page }) => {
    await expect(page.locator('#email')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Send reset link' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Back to sign in' })).toBeVisible()
  })

  test('empty email submit does not navigate', async ({ page }) => {
    await page.getByRole('button', { name: 'Send reset link' }).click()
    await expect(page).toHaveURL('/forgot-password')
    // Form is still visible (no success state transition)
    await expect(page.locator('#email')).toBeVisible()
  })

  test('valid email submit transitions to check-inbox state', async ({ page }) => {
    await page.locator('#email').fill('admin@example.org')
    await page.getByRole('button', { name: 'Send reset link' }).click()
    // Form hides and success message appears
    await expect(page.locator('#email')).not.toBeVisible()
    await expect(page.getByText('Check your inbox')).toBeVisible()
    await expect(page.getByRole('link', { name: 'Back to sign in' })).toBeVisible()
  })
})
