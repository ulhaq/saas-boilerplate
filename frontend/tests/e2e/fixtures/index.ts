import { test as base, expect, type BrowserContext, type Page } from '@playwright/test'
import { readFile } from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'
import type { AuthTokens } from '../setup/global-setup.ts'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const AUTH_DIR = path.join(__dirname, '../.auth')
const MEMBER_STATE = path.join(AUTH_DIR, 'member.json')

// Tokens are written once by global setup and never change during a run.
// Cache them so every test fixture avoids redundant file I/O.
let _tokens: AuthTokens | null = null

async function getTokens(): Promise<AuthTokens> {
  if (!_tokens) {
    let raw: string
    try {
      raw = await readFile(path.join(AUTH_DIR, 'tokens.json'), 'utf-8')
    } catch {
      throw new Error(
        '[auth fixture] .auth/tokens.json not found - run `npx playwright test` to trigger global setup first',
      )
    }
    _tokens = JSON.parse(raw) as AuthTokens
  }
  return _tokens
}

/**
 * Registers a context-level route stub for POST /v1/auth/refresh.
 *
 * Vue's authStore.initialize() calls this endpoint on every full-page navigation.
 * Stubbing it at the context level (rather than page level) ensures the handler
 * is active before the very first page event fires, and it survives navigations
 * within the test without needing to be re-registered.
 *
 * The real refresh endpoint uses token rotation (deletes old token, issues new
 * one). Stubbing it prevents that rotation from invalidating the shared token
 * that was acquired once in global setup.
 */
async function stubRefresh(context: BrowserContext, accessToken: string): Promise<void> {
  await context.route('**/v1/auth/refresh', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access_token: accessToken, token_type: 'bearer' }),
    }),
  )
}

/**
 * Authenticated test fixture for the admin user (admin@example.org / Owner role).
 * Overrides the `context` fixture so every test in the describe block starts with
 * the refresh stub in place - no login API call per test.
 */
export const test = base.extend({
  context: async ({ context }, use) => {
    const { admin } = await getTokens()
    await stubRefresh(context, admin)
    await use(context)
  },
})

/**
 * Authenticated test fixture for the member user (standard@example.org / Member role).
 * Creates a dedicated browser context so it is fully isolated from any admin
 * storageState that may be configured at the project level, then stubs refresh
 * with the member token.
 */
export const memberTest = base.extend({
  context: async ({ browser }, use) => {
    const { member } = await getTokens()
    const context = await browser.newContext({ storageState: MEMBER_STATE })
    await stubRefresh(context, member)
    await use(context)
    await context.close()
  },
})

/**
 * Stubs the three data fetches that authStore fires after a successful login
 * (fetchMe, fetchOrganizations, fetchSubscriptionStatus). Required in guest-context
 * tests where the access token returned by complete-registration / complete-invite
 * is synthetic and would 401 against the real backend, triggering a redirect back
 * to /login and making post-submit navigation assertions impossible.
 *
 * Pass a fake accessToken so the refresh stub can return a consistent value if the
 * app re-initialises after the redirect.
 */
export async function stubPostLoginFetches(page: Page, accessToken = 'fake-token'): Promise<void> {
  const now = new Date().toISOString()

  await page.route('**/v1/auth/refresh', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access_token: accessToken, token_type: 'bearer' }),
    }),
  )

  await page.route('**/v1/users/me', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 999,
        name: 'Test User',
        email: 'test@example.com',
        roles: [],
        created_at: now,
        updated_at: now,
      }),
    }),
  )

  await page.route('**/v1/organizations', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{ id: 1, name: 'Test Org', created_at: now, updated_at: now }]),
    }),
  )

  await page.route('**/v1/billing/subscriptions/current', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 1,
        organization_id: 1,
        plan_price_id: null,
        status: 'active',
        current_period_start: null,
        current_period_end: null,
        cancel_at_period_end: false,
        canceled_at: null,
        cancel_at: null,
        trial_end: null,
        plan_price: null,
        has_payment_method: false,
        trial_used: false,
        created_at: now,
        updated_at: now,
      }),
    }),
  )
}

export { expect }
