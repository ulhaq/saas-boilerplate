import { test, expect } from '../fixtures/index.js'

test.describe('Roles settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings/roles')
    await page.waitForURL('/settings/roles', { timeout: 10_000 })
  })

  test('roles list loads with seeded roles', async ({ page }) => {
    await expect(page.locator('table').getByText('Owner').first()).toBeVisible()
  })

  test('protected role shows "Protected" badge', async ({ page }) => {
    await expect(page.locator('table').getByText('Protected').first()).toBeVisible()
  })

  test('Add role button is visible for admin', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Add role' })).toBeVisible()
  })

  test('create role: fill name and save adds role to list', async ({ page }) => {
    const roleName = `E2E Role ${Date.now()}`
    await page.getByRole('button', { name: 'Add role' }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await dialog
      .locator('input[id="name"], input[placeholder*="Manager"], input[placeholder*="role"]')
      .first()
      .fill(roleName)
    await dialog.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByText(roleName)).toBeVisible({ timeout: 5000 })
  })

  test('opening actions on non-protected role shows edit and delete', async ({ page }) => {
    // Find a non-protected role row (standard/member role)
    const rows = page.locator('table tbody tr')
    const count = await rows.count()

    for (let i = 0; i < count; i++) {
      const row = rows.nth(i)
      const isProtected = await row.getByText('Protected').count()
      if (isProtected === 0) {
        // Open the actions dropdown
        await row.getByRole('button').last().click()
        await expect(page.getByRole('menuitem', { name: 'Edit' })).toBeVisible()
        await expect(page.getByRole('menuitem', { name: 'Delete' })).toBeVisible()
        // Close by pressing Escape
        await page.keyboard.press('Escape')
        break
      }
    }
  })

  test('opening actions on protected role shows only View permissions', async ({ page }) => {
    const rows = page.locator('table tbody tr')
    const count = await rows.count()

    for (let i = 0; i < count; i++) {
      const row = rows.nth(i)
      const isProtected = await row.getByText('Protected').count()
      if (isProtected > 0) {
        await row.getByRole('button').last().click()
        await expect(page.getByRole('menuitem', { name: 'View permissions' })).toBeVisible()
        await expect(page.getByRole('menuitem', { name: 'Edit' })).not.toBeVisible()
        await expect(page.getByRole('menuitem', { name: 'Delete' })).not.toBeVisible()
        await page.keyboard.press('Escape')
        break
      }
    }
  })

  test('manage permissions dialog shows permission checkboxes', async ({ page }) => {
    // Find a non-protected role
    const rows = page.locator('table tbody tr')
    const count = await rows.count()

    for (let i = 0; i < count; i++) {
      const row = rows.nth(i)
      const isProtected = await row.getByText('Protected').count()
      if (isProtected === 0) {
        await row.getByRole('button').last().click()
        await page.getByRole('menuitem', { name: 'Manage permissions' }).click()
        await expect(page.getByRole('dialog')).toBeVisible()
        await expect(
          page.getByRole('dialog').getByRole('heading', { name: 'Manage permissions' }),
        ).toBeVisible()
        await page.keyboard.press('Escape')
        break
      }
    }
  })
})
