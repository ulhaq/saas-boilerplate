/**
 * Product identity for the app.
 *
 * Deliberately import-free: it is loaded by `vite.config.ts` at build time as
 * well as by the app, so it must not pull in Vue, i18n or anything that needs
 * a browser.
 *
 * Values are interpolated into vue-i18n messages, so keep them free of the
 * message-syntax characters `{ } @ $ |`.
 *
 * The backend (`APP_NAME`, used in email) and the marketing site
 * (`site/src/config.ts`) have their own copies of the product name - keep them
 * in sync.
 */
export const BRAND = {
  name: 'SaaS Boilerplate',
  /** The marketing site: legal pages, OG image. */
  marketingOrigin: 'https://example.com',
  /** This app; auth pages canonically live here. */
  appOrigin: 'https://app.example.com',
} as const
