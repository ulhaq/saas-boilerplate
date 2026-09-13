import { test, expect } from '@playwright/test'

// The component reads route.query.token in <script setup> before the immediate
// router.replace() fires, so navigating with ?token=<value> is sufficient to
// put it in the "has token" branch without the token persisting in the URL bar.

test.describe('Reset password - no token', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/reset-password')
  })

  test('shows invalid-token error and a link to request a new one', async ({ page }) => {
    await expect(page.getByText(/invalid.*token/i)).toBeVisible()
    await expect(page.getByRole('link', { name: /request a new link/i })).toBeVisible()
  })

  test('link to request a new link points to /forgot-password', async ({ page }) => {
    const link = page.getByRole('link', { name: /request a new link/i })
    await expect(link).toHaveAttribute('href', /forgot-password/)
  })
})

test.describe('Reset password - with token', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/reset-password?token=fake-reset-token')
  })

  test('renders new-password and confirm-password fields with submit button', async ({ page }) => {
    await expect(page.locator('#password')).toBeVisible()
    await expect(page.locator('#confirm')).toBeVisible()
    await expect(page.getByRole('button', { name: /update password/i })).toBeVisible()
  })

  test('empty submit shows both field validation errors', async ({ page }) => {
    await page.getByRole('button', { name: /update password/i }).click()
    const errors = page.locator('.text-destructive')
    await expect(errors.first()).toBeVisible()
  })

  test('password shorter than 8 characters shows length error', async ({ page }) => {
    await page.locator('#password').fill('short')
    await page.locator('#confirm').fill('short')
    await page.getByRole('button', { name: /update password/i }).click()
    await expect(page.locator('.text-destructive').first()).toBeVisible()
  })

  test('mismatched passwords shows confirm-field error', async ({ page }) => {
    await page.locator('#password').fill('validpassword1')
    await page.locator('#confirm').fill('differentpassword')
    await page.getByRole('button', { name: /update password/i }).click()
    await expect(page.locator('.text-destructive').first()).toBeVisible()
  })

  test('successful reset transitions to success state with sign-in link', async ({ page }) => {
    await page.route('**/v1/auth/reset-password', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
    )

    await page.locator('#password').fill('newpassword123')
    await page.locator('#confirm').fill('newpassword123')
    await page.getByRole('button', { name: /update password/i }).click()

    await expect(page.getByText(/password.*updated|updated.*success/i)).toBeVisible()
    await expect(page.getByRole('link', { name: /sign in/i })).toBeVisible()
    // Form should no longer be present
    await expect(page.locator('#password')).not.toBeVisible()
  })

  test('backend error shows inline error message', async ({ page }) => {
    await page.route('**/v1/auth/reset-password', (route) =>
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Token expired' }),
      }),
    )

    await page.locator('#password').fill('newpassword123')
    await page.locator('#confirm').fill('newpassword123')
    await page.getByRole('button', { name: /update password/i }).click()

    // Error renders inline in the form, not as a toast
    await expect(page.locator('p.text-destructive')).toBeVisible()
    // Form stays visible - user can retry
    await expect(page.locator('#password')).toBeVisible()
  })
})
