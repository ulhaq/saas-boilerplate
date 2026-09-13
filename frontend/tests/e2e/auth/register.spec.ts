import { test, expect } from '@playwright/test'

test.describe('Register page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/register')
  })

  test('renders registration form', async ({ page }) => {
    await expect(page.locator('#email')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create an account' })).toBeVisible()
  })

  test('empty email shows validation error', async ({ page }) => {
    await page.getByRole('button', { name: 'Create an account' }).click()
    await expect(page.locator('.text-destructive')).toBeVisible()
  })

  test('invalid email format shows validation error', async ({ page }) => {
    await page.locator('#email').fill('not-an-email')
    await page.getByRole('button', { name: 'Create an account' }).click()
    await expect(page.locator('.text-destructive')).toBeVisible()
  })

  test('valid email submit transitions to check-inbox state', async ({ page }) => {
    const unique = `e2e-${Date.now()}@test.com`
    await page.locator('#email').fill(unique)
    await page.getByRole('button', { name: 'Create an account' }).click()
    // After successful submit the form disappears and success UI appears
    await expect(page.locator('#email')).not.toBeVisible()
    await expect(page.getByRole('link', { name: 'Back to sign in' })).toBeVisible()
  })

  test('already-registered email shows error', async ({ page }) => {
    await page.locator('#email').fill('admin@example.org')
    await page.getByRole('button', { name: 'Create an account' }).click()
    await expect(page.locator('.text-destructive')).toBeVisible()
  })
})
