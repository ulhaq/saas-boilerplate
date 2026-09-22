import { test, expect } from '@playwright/test'

test.describe('Confirm email change page', () => {
  test('no token shows invalid-link message', async ({ page }) => {
    await page.goto('/confirm-email-change')
    await expect(page.getByText(/invalid, expired, or has already been used/)).toBeVisible()
  })

  test('valid token confirms and offers sign-in', async ({ page }) => {
    await page.route('**/v1/auth/confirm-email-change', (route) =>
      route.fulfill({ status: 204, body: '' }),
    )
    await page.goto('/confirm-email-change?token=valid-token')

    await expect(page.getByText(/Your email has been changed/)).toBeVisible({ timeout: 5_000 })
    // Token is stripped from the URL once read.
    expect(page.url()).not.toContain('token=')
    await page.getByRole('button', { name: 'Sign in' }).click()
    await page.waitForURL(/\/login/, { timeout: 5_000 })
  })

  test('used or expired token shows invalid-link message', async ({ page }) => {
    await page.route('**/v1/auth/confirm-email-change', (route) =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error_code: 'token_invalid', msg: 'Token invalid' }),
      }),
    )
    await page.goto('/confirm-email-change?token=used-token')
    await expect(page.getByText(/invalid, expired, or has already been used/)).toBeVisible({
      timeout: 5_000,
    })
  })
})
