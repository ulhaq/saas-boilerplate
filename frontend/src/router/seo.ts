import { i18n } from '@/plugins/i18n'
import { BRAND } from '@/brand'
import { MARKETING_ORIGIN } from '@/platform/constants'

/**
 * The only indexable app pages, with their `seo.*` copy key. Everything else
 * is behind a login and noindexed; `public/robots.txt` mirrors this list.
 * Auth pages are deliberately not localized - they are linked from emails and
 * invites, so their URLs need to stay stable.
 */
const INDEXABLE_PAGES: Record<string, string> = {
  '/login': 'login',
  '/register': 'register',
  '/forgot-password': 'forgotPassword',
}

/**
 * Head tags for a route. Called from `App.vue` inside a `computed`, so it
 * re-runs on every navigation and language switch. The marketing pages live
 * outside this repo, on their own domain.
 */
export function buildRouteHead(path: string, breadcrumb?: string) {
  const { t, locale } = i18n.global

  const seoKey = INDEXABLE_PAGES[path]
  const title = seoKey
    ? t(`seo.${seoKey}.title`)
    : breadcrumb
      ? `${t(breadcrumb)} · ${t('app.name')}`
      : t('app.name')
  const description = t(`seo.${seoKey ?? 'app'}.description`)
  const canonical = seoKey ? `${BRAND.appOrigin}${path}` : `${MARKETING_ORIGIN}/`

  return {
    htmlAttrs: { lang: locale.value },
    title,
    link: seoKey ? [{ rel: 'canonical', href: canonical }] : [],
    meta: [
      { name: 'robots', content: seoKey ? 'index, follow' : 'noindex, nofollow' },
      { name: 'description', content: description },
      { property: 'og:title', content: seoKey ? title : t('seo.app.title') },
      { property: 'og:description', content: description },
      { property: 'og:url', content: canonical },
      { property: 'og:locale', content: locale.value === 'da' ? 'da_DK' : 'en_US' },
      { name: 'twitter:title', content: seoKey ? title : t('seo.app.title') },
      { name: 'twitter:description', content: description },
    ],
  }
}
