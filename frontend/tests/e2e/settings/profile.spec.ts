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

  test('email is read-only and changed through the confirmation dialog', async ({ page }) => {
    await expect(page.locator('input').last()).toBeDisabled()

    let body: Record<string, unknown> | null = null
    await page.route('**/v1/users/me/email', async (route) => {
      body = route.request().postDataJSON()
      await route.fulfill({ status: 202, contentType: 'application/json', body: 'null' })
    })

    await page.getByRole('button', { name: 'Change', exact: true }).click()
    const dialog = page.getByRole('dialog')
    await dialog.locator('#change-email-new').fill('alice.new@example.org')
    await dialog.locator('#change-email-password').fill('password')
    await dialog.getByRole('button', { name: 'Send confirmation link' }).click()

    await expect(page.getByRole('list').getByText('Check your new inbox')).toBeVisible({
      timeout: 5000,
    })
    expect(body).toMatchObject({ new_email: 'alice.new@example.org', password: 'password' })
    // Nothing changes until the link is confirmed.
    await expect(page.locator('input').last()).toHaveValue('admin@example.org')
  })
})
