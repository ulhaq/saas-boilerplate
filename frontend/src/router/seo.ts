import { i18n } from '@/plugins/i18n'
import {
  DEFAULT_LOCALE,
  INDEXABLE_ORIGINS,
  LOCALES,
  MARKETING_ORIGIN,
  localizedPath,
  lookupPath,
} from './public-routes'

// Paths outside the localized marketing set that still get their own copy.
// Auth pages aren't localized (see `public-routes.ts`), so they map directly.
const AUTH_SEO_KEYS: Record<string, string> = {
  '/login': 'login',
  '/register': 'register',
  '/forgot-password': 'forgotPassword',
}

/**
 * Build the head tags for a route. Called from `App.vue` inside a `computed`,
 * so it runs both during the SSG build (baking the tags into the emitted HTML)
 * and on the client (updating them on every navigation).
 *
 * Reading `locale.value` and calling `t()` keeps the computed subscribed to
 * locale changes, so switching language re-renders the tags.
 */
export function buildRouteHead(path: string, breadcrumb?: string) {
  const { t, locale } = i18n.global

  // Resolve to the canonical spelling first: a visitor may arrive at `/da`
  // while the canonical form is `/da/`, and both must yield the same tags.
  const marketing = lookupPath(path)
  const canonicalPath = marketing ? localizedPath(marketing.page, marketing.locale) : path
  const origin = INDEXABLE_ORIGINS[canonicalPath]
  const isPublic = origin !== undefined
  const seoKey = marketing?.page.seo ?? AUTH_SEO_KEYS[canonicalPath]

  // Public pages get their own copy; everything else falls back to the
  // breadcrumb label (for the browser tab) and the default landing meta
  // (those pages are noindexed, so the values are cosmetic).
  const title = seoKey
    ? t(`seo.${seoKey}.title`)
    : breadcrumb
      ? `${t(breadcrumb)} · ${t('app.name')}`
      : t('app.name')

  const description = t(`seo.${seoKey ?? 'landing'}.description`)
  const socialTitle = seoKey ? title : t('seo.landing.title')
  const canonical = isPublic ? `${origin}${canonicalPath}` : `${MARKETING_ORIGIN}/`

  const link: Record<string, string>[] = isPublic ? [{ rel: 'canonical', href: canonical }] : []

  // hreflang: tells search engines the page exists in both languages, and which
  // to serve when neither matches. Only the localized marketing pages have a
  // counterpart, so only they get alternates.
  if (marketing) {
    for (const alt of LOCALES) {
      link.push({
        rel: 'alternate',
        hreflang: alt,
        href: `${MARKETING_ORIGIN}${localizedPath(marketing.page, alt)}`,
      })
    }
    link.push({
      rel: 'alternate',
      hreflang: 'x-default',
      href: `${MARKETING_ORIGIN}${localizedPath(marketing.page, DEFAULT_LOCALE)}`,
    })
  }

  return {
    htmlAttrs: { lang: locale.value },
    title,
    link,
    meta: [
      { name: 'robots', content: isPublic ? 'index, follow' : 'noindex, nofollow' },
      { name: 'description', content: description },
      { property: 'og:title', content: socialTitle },
      { property: 'og:description', content: description },
      { property: 'og:url', content: canonical },
      { property: 'og:locale', content: locale.value === 'da' ? 'da_DK' : 'en_US' },
      { name: 'twitter:title', content: socialTitle },
      { name: 'twitter:description', content: description },
    ],
  }
}
