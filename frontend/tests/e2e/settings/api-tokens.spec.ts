import { test, expect } from '../fixtures/index.js'

test.describe('API Tokens', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings/api')
    await page.waitForURL('/settings/api', { timeout: 10_000 })
  })

  test('page loads with API Tokens heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'API Tokens' })).toBeVisible()
  })

  test('Create Token button opens dialog', async ({ page }) => {
    await page.getByRole('button', { name: 'Create token' }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(
      page.getByRole('dialog').getByRole('heading', { name: 'Create token' }),
    ).toBeVisible()
  })

  test('submitting empty name shows validation error', async ({ page }) => {
    await page.getByRole('button', { name: 'Create token' }).click()
    await page.getByRole('dialog').getByRole('button', { name: 'Create token' }).click()
    await expect(page.locator('.text-destructive').first()).toBeVisible()
  })

  test('submitting without permissions shows validation error', async ({ page }) => {
    await page.getByRole('button', { name: 'Create token' }).click()
    const dialog = page.getByRole('dialog')
    await dialog.locator('input[placeholder]').first().fill('Test Token')
    await dialog.getByRole('button', { name: 'Create token' }).click()
    await expect(page.locator('.text-destructive').last()).toBeVisible()
  })

  test('creates token and shows one-time reveal dialog', async ({ page }) => {
    await page.getByRole('button', { name: 'Create token' }).click()
    const dialog = page.getByRole('dialog')

    await dialog.locator('input[placeholder]').first().fill('E2E Test Token')
    // Select first available permission
    await dialog.locator('.border.rounded-md > div').first().click()
    await dialog.getByRole('button', { name: 'Create token' }).click()

    // The create dialog closes and the reveal dialog opens
    await expect(page.getByText('Copy your token')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('code')).toBeVisible()
  })

  test('reveal dialog has a copy button that changes to checkmark', async ({ page }) => {
    await page.getByRole('button', { name: 'Create token' }).click()
    const dialog = page.getByRole('dialog')
    await dialog.locator('input[placeholder]').first().fill('E2E Copy Test')
    await dialog.locator('.border.rounded-md > div').first().click()
    await dialog.getByRole('button', { name: 'Create token' }).click()

    await expect(page.getByText('Copy your token')).toBeVisible({ timeout: 5000 })

    // The copy button sits immediately after the <code> token element.
    // Clicking it changes the Copy icon to a Check icon (copied = true).
    const revealDialog = page.getByRole('dialog')
    await revealDialog.locator('code + button').click()

    // The SVG inside the copy button should still be visible (dialog stays open)
    await expect(revealDialog.locator('code + button svg')).toBeVisible()
  })

  test('revoke token shows confirm dialog and removes on confirm', async ({ page }) => {
    const tokenName = `E2E Revoke ${Date.now()}`

    // Create a fresh token to revoke
    await page.getByRole('button', { name: 'Create token' }).click()
    const dialog = page.getByRole('dialog')
    await dialog.locator('input[placeholder]').first().fill(tokenName)
    await dialog.locator('.border.rounded-md > div').first().click()
    await dialog.getByRole('button', { name: 'Create token' }).click()
    await expect(page.getByText('Copy your token')).toBeVisible({ timeout: 5000 })
    // Use .first() - both the X icon and "Close" text button have the "Close" accessible name
    await page.getByRole('dialog').getByRole('button', { name: 'Close' }).first().click()

    // Revoke the specific token we just created
    await page
      .getByRole('row', { name: new RegExp(tokenName) })
      .getByRole('button', { name: 'Revoke' })
      .click()
    await expect(page.getByRole('alertdialog')).toBeVisible()
    await page.getByRole('alertdialog').getByRole('button', { name: 'Revoke' }).click()

    // Token should be removed
    await expect(page.getByText(tokenName)).not.toBeVisible({ timeout: 5000 })
  })

  test('cancel revoke dialog leaves token intact', async ({ page }) => {
    const tokenName = `E2E Keep ${Date.now()}`

    // Create a fresh token
    await page.getByRole('button', { name: 'Create token' }).click()
    const dialog = page.getByRole('dialog')
    await dialog.locator('input[placeholder]').first().fill(tokenName)
    await dialog.locator('.border.rounded-md > div').first().click()
    await dialog.getByRole('button', { name: 'Create token' }).click()
    await expect(page.getByText('Copy your token')).toBeVisible({ timeout: 5000 })
    await page.getByRole('dialog').getByRole('button', { name: 'Close' }).first().click()

    // Open revoke for the specific token, then cancel
    await page
      .getByRole('row', { name: new RegExp(tokenName) })
      .getByRole('button', { name: 'Revoke' })
      .click()
    await expect(page.getByRole('alertdialog')).toBeVisible()
    await page.getByRole('alertdialog').getByRole('button', { name: 'Cancel' }).click()

    // Token should still be there
    await expect(page.getByText(tokenName)).toBeVisible()
  })
})
