import { test, expect, type Page } from '@playwright/test'
import { stubPostLoginFetches } from '../fixtures/index.js'

const FAKE_SETUP_TOKEN = 'fake-setup-token'

// Like reset-password, the component reads route.query.token in <script setup>
// before router.replace() fires, so ?token=<value> is enough to reach the
// "has token" branch.

test.describe('Verify email - no token', () => {
  test('shows error state with link back to /register', async ({ page }) => {
    await page.goto('/verify-email')
    await expect(page.getByText(/invalid.*link|invalid.*verify/i)).toBeVisible()
    await expect(page.getByRole('link', { name: /register again/i })).toBeVisible()
  })
})

test.describe('Verify email - invalid/expired token', () => {
  test('shows error state after failed verification', async ({ page }) => {
    await page.route('**/v1/auth/verify-email', (route) =>
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Token invalid or expired' }),
      }),
    )

    await page.goto('/verify-email?token=bad-token')

    await expect(page.getByText(/invalid.*link|invalid.*verify/i)).toBeVisible()
    await expect(page.getByRole('link', { name: /register again/i })).toBeVisible()
  })
})

test.describe('Verify email - valid token', () => {
  async function stubVerifyEmail(page: Page, setupToken = FAKE_SETUP_TOKEN) {
    await page.route('**/v1/auth/verify-email', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ setup_token: setupToken }),
      }),
    )
  }

  test('complete-profile form becomes visible after verification', async ({ page }) => {
    await stubVerifyEmail(page)
    await page.goto('/verify-email?token=valid-token')

    await expect(page.locator('#name')).toBeVisible()
    await expect(page.locator('#password')).toBeVisible()
    await expect(page.getByRole('button', { name: /get started/i })).toBeVisible()
  })

  test('empty submit shows name and password validation errors', async ({ page }) => {
    await stubVerifyEmail(page)
    await page.goto('/verify-email?token=valid-token')

    await page.getByRole('button', { name: /get started/i }).click()
    await expect(page.locator('.text-destructive').first()).toBeVisible()
  })

  test('name filled but password shorter than 8 chars shows password error', async ({ page }) => {
    await stubVerifyEmail(page)
    await page.goto('/verify-email?token=valid-token')

    await page.locator('#name').fill('Alice')
    await page.locator('#password').fill('short')
    await page.getByRole('button', { name: /get started/i }).click()
    await expect(page.locator('.text-destructive').first()).toBeVisible()
  })

  test('valid submission redirects to /settings/billing', async ({ page }) => {
    await stubVerifyEmail(page)

    // After completeRegistration the auth store calls fetchMe, fetchOrganizations,
    // and fetchSubscriptionStatus with the returned token. Stub all three so the
    // fake token doesn't 401 and trigger a redirect back to /login.
    await page.route('**/v1/auth/complete-registration', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access_token: 'fake-access-token', token_type: 'bearer' }),
      }),
    )
    await stubPostLoginFetches(page, 'fake-access-token')

    await page.goto('/verify-email?token=valid-token')
    await expect(page.locator('#name')).toBeVisible()

    await page.locator('#name').fill('Alice')
    await page.locator('#password').fill('securepassword123')
    await page.getByRole('button', { name: /get started/i }).click()

    await page.waitForURL('/settings/billing', { timeout: 10_000 })
    await expect(page).toHaveURL('/settings/billing')
  })
})
