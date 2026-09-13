import type { Router, RouteLocationNormalized, RouteRecordRaw } from 'vue-router'
import { routes as fileRoutes } from 'vue-router/auto-routes'
import { useAuthStore } from '@/platform/stores/auth'
import { useProfileStore } from '@/platform/stores/profile'
import { appConfig } from '@/platform/config'
import { i18n } from '@/plugins/i18n'
import {
  DEFAULT_LOCALE,
  LOCALES,
  MARKETING_PAGES,
  lookupPath,
  localizedPath,
  type Locale,
} from './public-routes'

function preferredLocale(): Locale {
  const saved = (
    typeof localStorage !== 'undefined' ? localStorage.getItem('locale') : null
  ) as Locale | null
  return saved && (LOCALES as readonly string[]).includes(saved) ? saved : DEFAULT_LOCALE
}

/**
 * Marketing pages are served from `/<locale>/<slug>` with a slug per language
 * (`/da/priser`, `/en/pricing`). unplugin-vue-router generates one record per
 * page file; we reuse each record's component under both localized paths and
 * drop the original bare path, which becomes a redirect instead.
 */
function buildRoutes(): RouteRecordRaw[] {
  const marketingFiles = new Set(MARKETING_PAGES.map((p) => p.file))

  // Everything that isn't a marketing page (the app and auth routes) keeps its
  // path untouched.
  const out: RouteRecordRaw[] = fileRoutes.filter(
    (r) => !marketingFiles.has(r.path),
  ) as RouteRecordRaw[]

  for (const page of MARKETING_PAGES) {
    const source = fileRoutes.find((r) => r.path === page.file) as RouteRecordRaw | undefined
    if (!source) continue

    for (const locale of LOCALES) {
      out.push({
        ...source,
        // Names must stay unique across the two locale variants.
        name: `${String(source.name ?? page.key)}___${locale}`,
        path: localizedPath(page, locale),
      } as RouteRecordRaw)
    }
  }

  // The bare, unlocalized paths (`/privacy-policy`, `/contact`, ...) no longer
  // exist as pages, but they are linked from emails, older pages and outside
  // sites, so keep them as redirects into the visitor's language rather than
  // letting them fall through to the catch-all 404.
  //
  // `meta.layout` is required: the host guard sends any non-landing route to
  // the app subdomain, so without it these would bounce to the app subdomain.
  for (const page of MARKETING_PAGES) {
    if (page.file === '/') continue
    out.push({
      path: page.file,
      redirect: () => localizedPath(page, preferredLocale()),
      meta: { layout: 'landing' },
    } as RouteRecordRaw)
  }

  const home = MARKETING_PAGES.find((p) => p.key === 'home')
  if (home) {
    out.push({
      path: '/',
      redirect: () => localizedPath(home, preferredLocale()),
      // `meta.layout` matters because the host guard routes landing paths to the
      // marketing domain; without it the root would be treated as an app route.
      meta: { layout: 'landing' },
    })
  }

  return out
}

export const routes = buildRoutes()

declare module 'vue-router' {
  interface RouteMeta {
    layout?: 'auth' | 'dashboard' | 'auto' | 'landing'
    requiresAuth?: boolean
    guestOnly?: boolean
    permission?: string
    planFeature?: string
    breadcrumb?: string
  }
}

/**
 * Resolve the locale a path should render in and apply it to i18n.
 *
 * Precedence: the locale in the URL wins; otherwise the visitor's saved choice;
 * otherwise Danish. Unprefixed app routes therefore keep whatever the visitor
 * last picked.
 */
function applyLocaleFromPath(path: string): void {
  // URL wins; otherwise the saved choice; otherwise Danish.
  const next: Locale = lookupPath(path)?.locale ?? preferredLocale()

  if (i18n.global.locale.value !== next) {
    i18n.global.locale.value = next
  }
}

/**
 * Attach the navigation guards. The router instance itself is created by
 * `ViteSSG` in `src/main.ts` (memory history during the prerender build, web
 * history in the browser), so this takes the router rather than owning it.
 *
 * Per-page meta tags are no longer applied here - `App.vue` drives them through
 * `useHead`, so they're baked into the prerendered HTML instead of being
 * written to `document` after hydration.
 */
export function installRouterGuards(router: Router): void {
  router.beforeEach(async (to: RouteLocationNormalized) => {
    // The URL is the authority on language: a localized marketing path always
    // renders in its own locale. This runs during the SSG build too, so each
    // prerendered page is emitted in the right language.
    applyLocaleFromPath(to.path)

    // No further guards during the SSG build: there is no browser to read a
    // hostname from, no session cookie to refresh, and every prerendered route
    // is public by definition.
    if (typeof window === 'undefined') return true

    const hostname = window.location.hostname
    const isLocalhost =
      hostname === 'localhost' || hostname === '127.0.0.1' || /^\d+\.\d+\.\d+\.\d+$/.test(hostname)

    if (!isLocalhost) {
      const isAppDomain = hostname.startsWith('app.')
      const isLandingRoute = to.meta.layout === 'landing'

      if (isAppDomain && isLandingRoute) {
        window.location.href = `${window.location.protocol}//${hostname.replace(/^app\./, '')}${to.fullPath}`
        return false
      }

      if (!isAppDomain && !isLandingRoute) {
        window.location.href = `${window.location.protocol}//app.${hostname}${to.fullPath}`
        return false
      }
    }

    const authStore = useAuthStore()

    if (!authStore.isInitialized) {
      await authStore.initialize()
      // `initialize()` loads the profile, which applies the signed-in user's
      // own language. That only happens on a full page load, so re-assert the
      // URL here - a localized marketing path must always win over it.
      applyLocaleFromPath(to.path)
    }

    if (to.meta.guestOnly && authStore.isAuthenticated) {
      return { path: appConfig.homeRoute }
    }

    if ((to.meta.requiresAuth || to.meta.permission) && !authStore.isAuthenticated) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }

    const profileStore = useProfileStore()

    if (to.meta.permission && !profileStore.hasPermission(to.meta.permission)) {
      return { path: appConfig.homeRoute }
    }

    const billingPaths = ['/settings/billing', '/billing/success', '/billing/cancel']
    const isBillingRoute = billingPaths.some((p) => to.path.startsWith(p))
    if (
      authStore.isAuthenticated &&
      !authStore.hasAppAccess &&
      to.meta.requiresAuth &&
      !isBillingRoute &&
      profileStore.hasPermission('manage:subscription')
    ) {
      return { path: '/settings/billing' }
    }
  })
}
