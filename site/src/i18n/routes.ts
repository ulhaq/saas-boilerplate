/**
 * The page inventory: one entry per page, with its public slug per locale.
 * Each page has a thin file per locale under `src/pages/<locale>/` that
 * renders the shared view from `src/views/`; this map is what links,
 * the language switch and the hreflang tags are built from.
 */
export const LOCALES = ['da', 'en'] as const
export type Locale = (typeof LOCALES)[number]

/** The locale `/` redirects to when the browser prefers neither. */
export const DEFAULT_LOCALE: Locale = 'da'

export const PAGES = {
  home: { da: '', en: '' },
  features: { da: 'funktioner', en: 'features' },
  pricing: { da: 'priser', en: 'pricing' },
  about: { da: 'om-os', en: 'about' },
  contact: { da: 'kontakt', en: 'contact' },
  // Linked from the app (LEGAL_PATHS) - do not rename without updating it.
  privacy: { da: 'privatlivspolitik', en: 'privacy-policy' },
  terms: { da: 'handelsbetingelser', en: 'terms' },
} as const satisfies Record<string, Record<Locale, string>>

export type PageKey = keyof typeof PAGES

/** `path('pricing', 'da')` -> `/da/priser/` */
export function path(page: PageKey, locale: Locale): string {
  const slug = PAGES[page][locale]
  return slug ? `/${locale}/${slug}/` : `/${locale}/`
}

export function localeFromUrl(url: URL): Locale {
  const first = url.pathname.split('/')[1]
  return (LOCALES as readonly string[]).includes(first) ? (first as Locale) : DEFAULT_LOCALE
}

/** Finds which page a URL is, so the language switch can link its twin. */
export function pageFromUrl(url: URL): PageKey | null {
  const [, locale, slug = ''] = url.pathname.replace(/\/$/, '').split('/')
  if (!(LOCALES as readonly string[]).includes(locale)) return null
  const entry = Object.entries(PAGES).find(([, slugs]) => slugs[locale as Locale] === slug)
  return entry ? (entry[0] as PageKey) : null
}
