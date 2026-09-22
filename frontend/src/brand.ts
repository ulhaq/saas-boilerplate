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
 * The backend has its own copy of the product name (`APP_NAME`, used in
 * email) - keep the two in sync.
 */
export const BRAND = {
  name: 'SaaS Boilerplate',
  /** The marketing site: legal pages, OG image. */
  marketingOrigin: 'https://example.com',
  /** This app; auth pages canonically live here. */
  appOrigin: 'https://app.example.com',
} as const
