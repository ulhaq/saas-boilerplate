import { test, expect } from '../fixtures/index.js'

test.describe('Organizations settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings/organizations')
    await page.waitForURL('/settings/organizations', { timeout: 10_000 })
  })

  test('organizations list loads with seeded orgs', async ({ page }) => {
    await expect(page.locator('table').getByText('Acme Corp')).toBeVisible()
  })

  test('Create organization button is visible', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Create organization' })).toBeVisible()
  })

  test('create organization: form opens and submitting valid name adds org to list', async ({
    page,
  }) => {
    const orgName = `E2E Org ${Date.now()}`
    await page.getByRole('button', { name: 'Create organization' }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await dialog.locator('input[placeholder*="Acme"], input[id="name"]').first().fill(orgName)
    await dialog.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByText(orgName)).toBeVisible({ timeout: 5000 })
  })

  test('View members opens members dialog', async ({ page }) => {
    // Open action menu for Acme Corp row
    const rows = page.locator('table tbody tr')
    await rows.first().getByRole('button').last().click()
    await page.getByRole('menuitem', { name: 'View members' }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(
      page.getByRole('dialog').getByRole('heading', { name: 'Organization users' }),
    ).toBeVisible()
    await page.keyboard.press('Escape')
  })
})
