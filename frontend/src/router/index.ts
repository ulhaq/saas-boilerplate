import type { Router, RouteRecordRaw } from 'vue-router'
import { createRouter, createWebHistory } from 'vue-router'
import { routes as fileRoutes } from 'vue-router/auto-routes'
import { useAuthStore } from '@/platform/stores/auth'
import { useProfileStore } from '@/platform/stores/profile'
import { appConfig } from '@/platform/config'

// The app has no page at `/`: it sends visitors to the home route, and the
// guard below bounces anyone signed out to the login page from there. The
// marketing site lives outside this repo, on its own domain.
const routes: RouteRecordRaw[] = [
  ...(fileRoutes as RouteRecordRaw[]),
  { path: '/', redirect: () => appConfig.homeRoute },
]

declare module 'vue-router' {
  interface RouteMeta {
    layout?: 'auth' | 'dashboard' | 'auto'
    requiresAuth?: boolean
    guestOnly?: boolean
    permission?: string
    planFeature?: string
    breadcrumb?: string
  }
}

export function createAppRouter(): Router {
  const router = createRouter({ history: createWebHistory(), routes })

  router.beforeEach(async (to) => {
    const authStore = useAuthStore()

    if (!authStore.isInitialized) {
      await authStore.initialize()
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

  return router
}
