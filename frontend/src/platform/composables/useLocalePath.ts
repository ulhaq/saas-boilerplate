import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import {
  DEFAULT_LOCALE,
  LOCALES,
  MARKETING_PAGES,
  lookupPath,
  localizedPath,
  type Locale,
} from '@/router/public-routes'

/**
 * Resolves marketing links for the language currently being viewed, so a
 * visitor on `/en/pricing` gets `/en/features` rather than being bounced back
 * into Danish. Templates use `localePath('features')` instead of a literal
 * path; the slug per locale lives in `@/router/public-routes`.
 */
export function useLocalePath() {
  const { locale } = useI18n()
  const route = useRoute()
  const router = useRouter()

  function currentLocale(): Locale {
    return (LOCALES as readonly string[]).includes(locale.value)
      ? (locale.value as Locale)
      : DEFAULT_LOCALE
  }

  /** `localePath('pricing')` -> `/da/priser` or `/en/pricing`. */
  function localePath(key: string, target?: Locale): string {
    const page = MARKETING_PAGES.find((p) => p.key === key)
    if (!page) return '/'
    return localizedPath(page, target ?? currentLocale())
  }

  /**
   * The current page in another language. Falls back to that language's home
   * page when the current route has no localized counterpart (an app or auth
   * route), so switching never 404s.
   */
  function switchLocalePath(target: Locale): string {
    const match = lookupPath(route.path)
    return match ? localizedPath(match.page, target) : `/${target}`
  }

  /** Switch language: persist the choice and move to the matching URL. */
  async function setLocale(target: Locale): Promise<void> {
    locale.value = target
    try {
      localStorage.setItem('locale', target)
    } catch {
      // Private mode or blocked storage - the URL still carries the language.
    }
    if (lookupPath(route.path)) {
      await router.push(switchLocalePath(target))
    }
  }

  return { localePath, switchLocalePath, setLocale, currentLocale }
}
