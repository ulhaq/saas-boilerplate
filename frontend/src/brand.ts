/**
 * Product identity - the one place to edit when starting a new product.
 *
 * Deliberately import-free: it is loaded by `vite.config.ts` (via
 * `router/public-routes.ts`) at build time as well as by the app, so it must
 * not pull in Vue, i18n or anything that needs a browser.
 *
 * Values are interpolated into vue-i18n messages, so keep them free of the
 * message-syntax characters `{ } @ $ |`.
 *
 * The backend has its own copy of the product name (`APP_NAME`, used in
 * email) - keep the two in sync.
 */
export const BRAND = {
  name: 'SaaS Boilerplate',
  /** Public marketing site (canonical URLs, sitemap, OG tags). */
  marketingOrigin: 'https://example.com',
  /** Signed-in application; auth pages canonically live here. */
  appOrigin: 'https://app.example.com',
  /** Fallback when `VITE_API_DOCS_URL` is unset. */
  apiDocsUrl: 'https://api.example.com/redoc',
  supportEmail: 'hello@example.com',
  /** Shown on the legal pages. */
  legalEntity: {
    name: 'Example Company ApS',
    registrationLabel: 'CVR',
    registrationNumber: '00000000',
    address: 'Example Street 1, 1000 Copenhagen, Denmark',
  },
} as const
