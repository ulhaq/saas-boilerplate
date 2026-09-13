import { test, expect } from '../fixtures/index.js'
import type { Page } from '@playwright/test'

// These tests cover invite states that require an authenticated session.
// The admin fixture (admin@example.org / Owner) is used throughout.
// Unauthenticated states (invalid token, new-user form) live in
// tests/e2e/auth/invite.spec.ts.

const ADMIN_EMAIL = 'admin@example.org'

function stubInviteStatus(page: Page, response: { email: string; user_exists: boolean }) {
  return page.route('**/v1/auth/invite-status', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(response),
    }),
  )
}

test.describe('Invite page - existing user (email matches logged-in user)', () => {
  test('shows one-click accept button, no name/password form', async ({ page }) => {
    await stubInviteStatus(page, { email: ADMIN_EMAIL, user_exists: true })
    await page.goto('/invite?token=valid-invite-token')

    await expect(
      page.getByRole('button', { name: `Accept invitation as ${ADMIN_EMAIL}` }),
    ).toBeVisible({ timeout: 5_000 })
    await expect(page.locator('#name')).not.toBeVisible()
    await expect(page.locator('#password')).not.toBeVisible()
  })

  test('clicking accept redirects to /', async ({ page }) => {
    await stubInviteStatus(page, { email: ADMIN_EMAIL, user_exists: true })
    await page.route('**/v1/auth/complete-invite', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access_token: 'fake-access-token', token_type: 'bearer' }),
      }),
    )
    // Stub refresh so the new fake token doesn't break the next initialize() call
    await page.route('**/v1/auth/refresh', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access_token: 'fake-access-token', token_type: 'bearer' }),
      }),
    )

    await page.goto('/invite?token=valid-invite-token')
    await expect(
      page.getByRole('button', { name: `Accept invitation as ${ADMIN_EMAIL}` }),
    ).toBeVisible({ timeout: 5_000 })

    await page.getByRole('button', { name: `Accept invitation as ${ADMIN_EMAIL}` }).click()
    await page.waitForURL('/', { timeout: 10_000 })
    await expect(page).toHaveURL('/')
  })
})

test.describe('Invite page - wrong account (invite email differs from logged-in user)', () => {
  test('shows wrong-account message and Logout button', async ({ page }) => {
    await stubInviteStatus(page, { email: 'someone-else@example.com', user_exists: true })
    await page.goto('/invite?token=valid-invite-token')

    // The component shows a "logged in as wrong account" message
    await expect(page.getByText(/wrong.*account|logout.*first|logged in as/i).first()).toBeVisible({
      timeout: 5_000,
    })
    await expect(page.getByRole('button', { name: /log.*out|logout/i })).toBeVisible()
  })

  test('clicking logout clears session and reloads with token in URL', async ({ page }) => {
    await stubInviteStatus(page, { email: 'someone-else@example.com', user_exists: true })
    await page.route('**/v1/auth/logout', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
    )

    await page.goto('/invite?token=valid-invite-token')
    await expect(page.getByRole('button', { name: /log.*out|logout/i })).toBeVisible({
      timeout: 5_000,
    })

    await page.getByRole('button', { name: /log.*out|logout/i }).click()

    // The component does window.location.href = /invite?token=... after logout
    // which is a full page reload - wait for the URL to contain the token again.
    await page.waitForURL(/\/invite.*token=/, { timeout: 10_000 })
    expect(page.url()).toContain('token=')
  })
})
