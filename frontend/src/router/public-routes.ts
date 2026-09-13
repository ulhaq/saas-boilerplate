/**
 * The public route inventory. It imports nothing but the import-free
 * `brand.ts`, so it can be loaded from both the app (via `./seo.ts`) and
 * `vite.config.ts`, which needs the prerender list and sitemap at build time
 * and cannot pull in the i18n singleton.
 */
import { BRAND } from '../brand'

export const MARKETING_ORIGIN: string = BRAND.marketingOrigin
export const APP_ORIGIN: string = BRAND.appOrigin

export const LOCALES = ['da', 'en'] as const
export type Locale = (typeof LOCALES)[number]

/** The locale a bare, unprefixed marketing URL resolves to. */
export const DEFAULT_LOCALE: Locale = 'da'

/**
 * Marketing pages, one entry per page.
 *
 * `file` is the path unplugin-vue-router generates from `src/**\/pages`; it is
 * how we find the component to reuse. `slugs` are the public, per-locale URL
 * segments, so every page is reachable at `/<locale>/<slug>`. `seo` names the
 * key under the `seo.*` namespace in the locale files.
 *
 * This is the single source of truth: routes, canonical/hreflang tags, the
 * prerender list and the sitemap are all derived from it.
 */
export interface MarketingPage {
  key: string
  file: string
  seo: string
  slugs: Record<Locale, string>
}

export const MARKETING_PAGES: MarketingPage[] = [
  { key: 'home', file: '/', seo: 'landing', slugs: { da: '', en: '' } },
  { key: 'pricing', file: '/pricing', seo: 'pricing', slugs: { da: 'priser', en: 'pricing' } },
  {
    key: 'features',
    file: '/features',
    seo: 'features',
    slugs: { da: 'funktioner', en: 'features' },
  },
  { key: 'about', file: '/about', seo: 'about', slugs: { da: 'om-os', en: 'about' } },
  { key: 'contact', file: '/contact', seo: 'contact', slugs: { da: 'kontakt', en: 'contact' } },
  {
    key: 'privacy',
    file: '/privacy-policy',
    seo: 'privacy',
    slugs: { da: 'privatlivspolitik', en: 'privacy-policy' },
  },
  {
    key: 'terms',
    file: '/terms',
    seo: 'terms',
    slugs: { da: 'handelsbetingelser', en: 'terms' },
  },
]

/**
 * `/da/priser`, `/en/pricing`, … - and `/da/` / `/en/` for the home page.
 *
 * The locale root keeps a trailing slash because it is a section root, the way
 * the marketing site root is `${MARKETING_ORIGIN}/`, and because the prerendered file
 * really does live at `dist/da/index.html`. Sub-pages have no trailing slash.
 */
export function localizedPath(page: MarketingPage, locale: Locale): string {
  const slug = page.slugs[locale]
  return slug ? `/${locale}/${slug}` : `/${locale}/`
}

/** Every localized marketing path, i.e. what `vite-ssg` prerenders. */
export const MARKETING_ROUTES: string[] = MARKETING_PAGES.flatMap((page) =>
  LOCALES.map((locale) => localizedPath(page, locale)),
)

/**
 * Auth pages: indexed, but canonically on the app subdomain because the host
 * guard in `./index.ts` redirects them there. Deliberately *not* localized -
 * they carry session state and are linked from emails and invites, so their
 * URLs need to stay stable.
 */
export const APP_AUTH_ROUTES = ['/login', '/register', '/forgot-password'] as const

/** Every indexable path mapped to the origin it canonically lives on. */
export const INDEXABLE_ORIGINS: Record<string, string> = {
  ...Object.fromEntries(MARKETING_ROUTES.map((path) => [path, MARKETING_ORIGIN])),
  ...Object.fromEntries(APP_AUTH_ROUTES.map((path) => [path, APP_ORIGIN])),
}

/**
 * Reverse lookup: localized path -> the page and locale it belongs to.
 *
 * Use `lookupPath()` rather than indexing this directly - vue-router matches
 * trailing slashes loosely, so `route.path` can arrive either way.
 */
export const PATH_LOOKUP: Record<string, { page: MarketingPage; locale: Locale }> =
  Object.fromEntries(
    MARKETING_PAGES.flatMap((page) =>
      LOCALES.map((locale) => [localizedPath(page, locale), { page, locale }] as const),
    ),
  )

/** `PATH_LOOKUP` with trailing slashes treated as insignificant. */
export function lookupPath(path: string): { page: MarketingPage; locale: Locale } | undefined {
  const alt = path.endsWith('/') ? path.slice(0, -1) : `${path}/`
  return PATH_LOOKUP[path] ?? PATH_LOOKUP[alt]
}
