import { test, expect } from '../fixtures/index.js'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForURL('/', { timeout: 10_000 })
  })

  test('loads and shows stat cards for admin', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
    await expect(page.getByText('Total Users')).toBeVisible()
    await expect(page.getByText('Organizations')).toBeVisible()
    await expect(page.getByText('Roles').first()).toBeVisible()
    await expect(page.getByText('Permissions')).toBeVisible()
  })

  test('stat cards show numeric values for admin (all permissions)', async ({ page }) => {
    // Admin has read:user, read:role, read:permission so no '-' dashes expected
    const cards = page.locator('.grid > div')
    await expect(cards.first()).not.toContainText('-')
  })

  test('unauthenticated visit redirects to login', async ({ browser }) => {
    const ctx = await browser.newContext()
    const page = await ctx.newPage()
    await page.goto('/')
    await page.waitForURL(/\/login/)
    expect(page.url()).toContain('/login')
    await ctx.close()
  })

  test('redirect param is preserved when bounced to login', async ({ browser }) => {
    const ctx = await browser.newContext()
    const page = await ctx.newPage()
    await page.goto('/')
    await page.waitForURL(/\/login/)
    expect(page.url()).toContain('redirect=/')
    await ctx.close()
  })
})
