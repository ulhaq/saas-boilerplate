import { request, type FullConfig } from '@playwright/test'
import { mkdir, writeFile } from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const AUTH_DIR = path.join(__dirname, '../.auth')

/**
 * Logs in as `email`, switches to org 1 (Acme Corp), and returns the resulting
 * access token. Uses Playwright's request context directly - no browser needed.
 *
 * Performing the org switch here resets any "active org" drift caused by
 * create-organization tests from previous runs (the backend returns a token for
 * the most-recently-active org on login). Running once per test suite means the
 * switch-organization DB write is made exactly once instead of once per test.
 */
async function acquireToken(baseURL: string, email: string, password: string): Promise<string> {
  const ctx = await request.newContext({ baseURL })

  try {
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)

    const loginRes = await ctx.post('/v1/auth/token', {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: form.toString(),
    })

    if (!loginRes.ok()) {
      throw new Error(
        `[global-setup] Login failed for ${email}: HTTP ${loginRes.status()} - is the backend running?`,
      )
    }

    const { access_token: loginToken } = (await loginRes.json()) as { access_token: string }
    if (!loginToken) {
      throw new Error(`[global-setup] Login for ${email} returned no access_token`)
    }

    const switchRes = await ctx.post('/v1/auth/switch-organization', {
      headers: {
        Authorization: `Bearer ${loginToken}`,
        'Content-Type': 'application/json',
      },
      data: JSON.stringify({ organization_id: 1 }),
    })

    if (!switchRes.ok()) {
      throw new Error(
        `[global-setup] switch-organization to org 1 failed for ${email}: HTTP ${switchRes.status()}`,
      )
    }

    const { access_token } = (await switchRes.json()) as { access_token: string }
    if (!access_token) {
      throw new Error(`[global-setup] switch-organization for ${email} returned no access_token`)
    }

    return access_token
  } finally {
    await ctx.dispose()
  }
}

export type AuthTokens = {
  admin: string
  member: string
}

export default async function globalSetup(config: FullConfig): Promise<void> {
  // baseURL lives on each project's use block (the top-level `use` in defineConfig
  // gets merged into projects at runtime). Pick the first project that declares one.
  const baseURL =
    (config.projects.find((p) => p.use.baseURL)?.use.baseURL as string | undefined) ??
    'http://localhost:5173'

  await mkdir(AUTH_DIR, { recursive: true })

  // Both logins are independent (different DB rows) - run in parallel.
  const [admin, member] = await Promise.all([
    acquireToken(baseURL, 'admin@example.org', 'password'),
    acquireToken(baseURL, 'standard@example.org', 'password'),
  ])

  const tokens: AuthTokens = { admin, member }
  await writeFile(path.join(AUTH_DIR, 'tokens.json'), JSON.stringify(tokens, null, 2))
}
