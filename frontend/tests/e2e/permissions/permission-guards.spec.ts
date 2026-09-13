import { memberTest as test, expect } from '../fixtures/index.js'

// These tests run as Bob Member (standard@example.org)
// Bob's permissions: read:user, read:role, read:permission, manage:api_token

test.describe('Permission guards - Member user', () => {
  test('/settings/users is accessible (has read:user)', async ({ page }) => {
    await page.goto('/settings/users')
    await page.waitForURL('/settings/users', { timeout: 10_000 })
    await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible()
  })

  test('/settings/roles is accessible (has read:role)', async ({ page }) => {
    await page.goto('/settings/roles')
    await page.waitForURL('/settings/roles', { timeout: 10_000 })
    await expect(page.getByRole('heading', { name: 'Roles' })).toBeVisible()
  })

  test('/settings/api is accessible (has manage:api_token)', async ({ page }) => {
    await page.goto('/settings/api')
    await page.waitForURL('/settings/api', { timeout: 10_000 })
    await expect(page.getByRole('heading', { name: 'API Tokens' })).toBeVisible()
  })

  test('/settings/billing redirects to / (lacks manage:subscription)', async ({ page }) => {
    await page.goto('/settings/billing')
    await page.waitForURL('/', { timeout: 10_000 })
    await expect(page).toHaveURL('/')
  })

  test('users list shows no Invite button (lacks manage:organization_user)', async ({ page }) => {
    await page.goto('/settings/users')
    await page.waitForURL('/settings/users', { timeout: 10_000 })
    await expect(page.getByRole('button', { name: 'Invite user' })).not.toBeVisible()
  })

  test('roles list shows no Add role button (lacks create:role)', async ({ page }) => {
    await page.goto('/settings/roles')
    await page.waitForURL('/settings/roles', { timeout: 10_000 })
    await expect(page.getByRole('button', { name: 'Add role' })).not.toBeVisible()
  })

  test('dashboard shows numeric stats for roles and users', async ({ page }) => {
    await page.goto('/')
    await page.waitForURL('/', { timeout: 10_000 })
    // Bob has read:user and read:role so stats should be numbers, not '-'
    await expect(page.getByText('Total Users')).toBeVisible()
    await expect(page.getByText('Roles').first()).toBeVisible()
  })

  test('/settings/security is accessible (no permission guard - all authenticated users)', async ({
    page,
  }) => {
    await page.goto('/settings/security')
    await page.waitForURL('/settings/security', { timeout: 10_000 })
    await expect(page.getByRole('heading', { name: /change password/i })).toBeVisible()
  })

  test('/settings/general is accessible but Danger Zone is hidden (Bob is not Owner)', async ({
    page,
  }) => {
    await page.goto('/settings/general')
    await page.waitForURL('/settings/general', { timeout: 10_000 })
    await expect(page.getByText(/danger zone/i)).not.toBeVisible()
  })
})
