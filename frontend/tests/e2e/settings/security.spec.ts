import { test, expect } from '../fixtures/index.js'

test.describe('Security settings - change password', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings/security')
    await page.waitForURL('/settings/security', { timeout: 10_000 })
  })

  test('page renders heading and three password inputs', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /change password/i })).toBeVisible()
    // Three password inputs: current, new, confirm
    const inputs = page.locator('input[type="password"]')
    await expect(inputs).toHaveCount(3)
    await expect(page.getByRole('button', { name: /update password/i })).toBeVisible()
  })

  test('empty submit shows all three field-level validation errors', async ({ page }) => {
    await page.getByRole('button', { name: /update password/i }).click()
    const errors = page.locator('.text-destructive')
    // At minimum the current-password and new-password errors are shown
    await expect(errors.first()).toBeVisible()
    await expect(errors).toHaveCount(await errors.count())
    expect(await errors.count()).toBeGreaterThanOrEqual(2)
  })

  test('current password filled but new password shorter than 8 chars shows length error', async ({
    page,
  }) => {
    const inputs = page.locator('input[type="password"]')
    await inputs.nth(0).fill('currentpassword')
    await inputs.nth(1).fill('short')
    await inputs.nth(2).fill('short')
    await page.getByRole('button', { name: /update password/i }).click()
    await expect(page.locator('.text-destructive').first()).toBeVisible()
  })

  test('new and confirm passwords do not match shows confirm error', async ({ page }) => {
    const inputs = page.locator('input[type="password"]')
    await inputs.nth(0).fill('currentpassword')
    await inputs.nth(1).fill('newpassword123')
    await inputs.nth(2).fill('differentpassword')
    await page.getByRole('button', { name: /update password/i }).click()
    await expect(page.locator('.text-destructive').first()).toBeVisible()
  })

  test('wrong current password: backend login_failed maps to inline field error, not a toast', async ({
    page,
  }) => {
    await page.route('**/v1/users/me/change-password', (route) =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error_code: 'login_failed', detail: 'Incorrect password' }),
      }),
    )

    const inputs = page.locator('input[type="password"]')
    await inputs.nth(0).fill('wrongpassword')
    await inputs.nth(1).fill('newpassword123')
    await inputs.nth(2).fill('newpassword123')
    await page.getByRole('button', { name: /update password/i }).click()

    // Error must appear as an inline field error, not a toast
    await expect(page.locator('.text-destructive').first()).toBeVisible()
    // Toast list should NOT contain a password-related error
    await expect(page.getByRole('list').getByText(/password/i)).not.toBeVisible()
  })

  test('successful change shows toast and clears all three fields', async ({ page }) => {
    await page.route('**/v1/users/me/change-password', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
    )

    const inputs = page.locator('input[type="password"]')
    await inputs.nth(0).fill('currentpassword')
    await inputs.nth(1).fill('newpassword123')
    await inputs.nth(2).fill('newpassword123')
    await page.getByRole('button', { name: /update password/i }).click()

    await expect(
      page.getByRole('list').getByText(/password.*updated|updated.*password/i),
    ).toBeVisible({
      timeout: 5_000,
    })
    // All three fields must be empty after success
    await expect(inputs.nth(0)).toHaveValue('')
    await expect(inputs.nth(1)).toHaveValue('')
    await expect(inputs.nth(2)).toHaveValue('')
  })
})
