import { readFile } from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'
import { test, expect } from '../fixtures/index.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

test.describe('Billing settings', () => {
  test('billing page loads and shows current plan', async ({ page }) => {
    await page.goto('/settings/billing')
    await page.waitForURL('/settings/billing', { timeout: 10_000 })
    await expect(page.getByRole('heading', { name: 'Subscription' })).toBeVisible()
    // Seed creates a Free active subscription
    await expect(page.getByText('Free').first()).toBeVisible()
  })

  test('subscribe button triggers checkout POST request', async ({ page }) => {
    // Block actual navigation to Stripe
    await page.route('**checkout.stripe.com**', (route) => route.abort())

    await page.goto('/settings/billing')
    await page.waitForURL('/settings/billing', { timeout: 10_000 })

    const subscribeButton = page
      .getByRole('button', { name: /Subscribe|Start free trial/i })
      .first()
    const hasPaidPlan = await subscribeButton.isVisible().catch(() => false)

    if (hasPaidPlan) {
      const [checkoutRequest] = await Promise.all([
        page.waitForRequest((req) => req.url().includes('/v1/billing') && req.method() === 'POST', {
          timeout: 5000,
        }),
        subscribeButton.click(),
      ])
      expect(checkoutRequest.method()).toBe('POST')
    }
  })
})

test.describe('Billing gate - subscription guard', () => {
  // The router redirects authenticated users who have manage:subscription but no
  // active subscription to /settings/billing from every other protected route.
  // We verify this by stubbing the subscription status fetch at the context level
  // (before any navigation) so authStore.initialize() sees an inactive subscription.
  //
  // A fresh browser context is created manually so the stub is in place before the
  // very first network request, which the existing `test` fixture context won't
  // guarantee for subscription fetches outside the refresh stub.
  test('visiting a protected route redirects to /settings/billing when subscription is inactive', async ({
    browser,
  }) => {
    const tokensRaw = await readFile(path.join(__dirname, '../.auth/tokens.json'), 'utf-8')
    const { admin } = JSON.parse(tokensRaw) as { admin: string; member: string }

    const context = await browser.newContext()

    await context.route('**/v1/auth/refresh', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access_token: admin, token_type: 'bearer' }),
      }),
    )

    await context.route('**/v1/billing/subscriptions/current', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          organization_id: 1,
          plan_price_id: null,
          status: 'canceled',
          current_period_start: null,
          current_period_end: null,
          cancel_at_period_end: false,
          canceled_at: null,
          cancel_at: null,
          trial_end: null,
          plan_price: null,
          has_payment_method: false,
          trial_used: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }),
      }),
    )

    const page = await context.newPage()
    await page.goto('/settings/users')
    await page.waitForURL('/settings/billing', { timeout: 10_000 })
    await expect(page).toHaveURL('/settings/billing')

    await context.close()
  })
})

test.describe('Billing redirect pages', () => {
  test('/billing/success renders success message', async ({ page }) => {
    await page.goto('/billing/success')
    await expect(page.getByText(/success|Payment|subscription/i).first()).toBeVisible()
  })

  test('/billing/cancel renders cancel message', async ({ page }) => {
    await page.goto('/billing/cancel')
    await expect(page.getByText(/cancel|back|subscription/i).first()).toBeVisible()
  })
})
