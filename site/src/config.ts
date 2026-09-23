/**
 * Site identity and environment.
 *
 * The site is standalone: it shares no code with the app (`frontend/`) or the
 * backend. Keep `name` in sync with `frontend/src/brand.ts` and the backend
 * `APP_NAME`, and keep the legal slugs in `i18n/routes.ts` in sync with
 * `LEGAL_PATHS` in `frontend/src/platform/constants.ts` - the app links there.
 */
export const SITE = {
  name: 'SaaS Boilerplate',
  supportEmail: 'hello@example.com',
  /** Shown on the legal pages and in the footer. */
  legalEntity: {
    name: 'Example Company ApS',
    registrationLabel: 'CVR',
    registrationNumber: '00000000',
    address: 'Example Street 1, 1000 Copenhagen, Denmark',
  },
} as const

const env = import.meta.env

/** The signed-in app; login and sign-up links point here. */
export const APP_URL: string = (env.PUBLIC_APP_URL || 'https://app.example.com').replace(/\/$/, '')

/** Empty hides the API docs link in the footer. */
export const API_DOCS_URL: string = env.PUBLIC_API_DOCS_URL || ''

/**
 * `signup` sends visitors to the app's registration page; `waitlist` swaps
 * every call to action for the waitlist form (pre-launch).
 */
export const CTA_MODE: 'signup' | 'waitlist' =
  env.PUBLIC_CTA_MODE === 'waitlist' ? 'waitlist' : 'signup'

/** Cookieless Umami analytics; the script is only added when both are set. */
export const UMAMI = {
  scriptUrl: env.PUBLIC_UMAMI_SCRIPT_URL || '',
  websiteId: env.PUBLIC_UMAMI_WEBSITE_ID || '',
}

export const appUrl = (path: string) => `${APP_URL}${path}`
