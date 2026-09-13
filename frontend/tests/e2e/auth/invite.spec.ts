import { test, expect, type Page } from '@playwright/test'
import { stubPostLoginFetches } from '../fixtures/index.js'

// These tests cover the unauthenticated invite states: invalid token, new-user
// form. Authenticated states (existing-user, wrong-account) are in
// tests/e2e/settings/invite-authenticated.spec.ts where the admin fixture is
// available.

function stubInviteStatus(
  page: Page,
  response: { email: string; user_exists: boolean } | null,
  status = 200,
) {
  return page.route('**/v1/auth/invite-status', (route) =>
    response === null
      ? route.fulfill({
          status,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Token invalid or expired' }),
        })
      : route.fulfill({
          status,
          contentType: 'application/json',
          body: JSON.stringify(response),
        }),
  )
}

test.describe('Invite page - no token', () => {
  test('shows invalid-link error and contact-admin message', async ({ page }) => {
    await page.goto('/invite')
    await expect(page.getByText(/invalid.*link|invalid/i).first()).toBeVisible()
    await expect(page.getByText('Please ask your admin to send a new invitation.')).toBeVisible()
  })
})

test.describe('Invite page - invalid/expired token', () => {
  test('shows invalid-link error after failed status check', async ({ page }) => {
    await stubInviteStatus(page, null, 400)
    await page.goto('/invite?token=bad-token')
    await expect(page.getByText(/invalid.*link|invalid/i).first()).toBeVisible()
  })
})

test.describe('Invite page - new user', () => {
  const INVITE_EMAIL = 'newuser@example.com'

  async function gotoWithNewUser(page: Page) {
    await stubInviteStatus(page, { email: INVITE_EMAIL, user_exists: false })
    await page.goto('/invite?token=valid-invite-token')
    // Wait for the async onMounted status check to resolve
    await expect(page.locator('#name')).toBeVisible({ timeout: 5_000 })
  }

  test('shows name and password form', async ({ page }) => {
    await gotoWithNewUser(page)
    await expect(page.locator('#name')).toBeVisible()
    await expect(page.locator('#password')).toBeVisible()
    await expect(page.getByRole('button', { name: /accept/i })).toBeVisible()
  })

  test('empty submit shows name and password validation errors', async ({ page }) => {
    await gotoWithNewUser(page)
    await page.getByRole('button', { name: /accept/i }).click()
    await expect(page.locator('.text-destructive').first()).toBeVisible()
  })

  test('name filled but password shorter than 8 chars shows password error', async ({ page }) => {
    await gotoWithNewUser(page)
    await page.locator('#name').fill('Bob')
    await page.locator('#password').fill('short')
    await page.getByRole('button', { name: /accept/i }).click()
    await expect(page.locator('.text-destructive').first()).toBeVisible()
  })

  test('valid submission redirects to /', async ({ page }) => {
    await gotoWithNewUser(page)

    // After completeInvite the auth store calls fetchMe, fetchOrganizations,
    // and fetchSubscriptionStatus with the returned token. Stub all so the
    // fake token doesn't 401 and loop back to /login.
    await page.route('**/v1/auth/complete-invite', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access_token: 'fake-access-token', token_type: 'bearer' }),
      }),
    )
    await stubPostLoginFetches(page, 'fake-access-token')

    await page.locator('#name').fill('Bob')
    await page.locator('#password').fill('securepassword123')
    await page.getByRole('button', { name: /accept/i }).click()

    await page.waitForURL('/', { timeout: 10_000 })
    await expect(page).toHaveURL('/')
  })
})
