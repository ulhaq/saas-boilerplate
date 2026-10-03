import type { RouteLocationNormalized, RouteLocationRaw } from 'vue-router'
import { useSubscriptionStore } from '@/billing/stores/subscription'
import type { Entitlements } from '@/platform/entitlements'
import { useProfileStore } from '@/platform/stores/profile'
import { i18n } from '@/plugins/i18n'

export const BILLING_ROUTE = '/settings/billing'
const BILLING_PATHS = [BILLING_ROUTE, '/billing/success', '/billing/cancel']

/** The organization's plan, as the platform's `Entitlements`. */
export function useBillingEntitlements(): Entitlements {
  const subscription = useSubscriptionStore()
  const profile = useProfileStore()
  return {
    hasFeature: subscription.hasFeature,
    limitFor: subscription.limitFor,
    load: subscription.fetchSubscriptionStatus,
    loadLimits: subscription.fetchUsage,
    clear: subscription.clear,
    planSummary: () => {
      const status = subscription.subscriptionStatus
      const { t, te } = i18n.global
      const key = `subscription.status.${status}`
      return {
        label: !status ? '-' : te(key) ? t(key) : status,
        route: profile.hasPermission('manage:subscription') ? BILLING_ROUTE : null,
      }
    },
  }
}

/**
 * Mirrors the backend access policy: an organization without a usable
 * subscription is sent to the billing page - if the user can act on it.
 */
export function requireAppAccess(to: RouteLocationNormalized): RouteLocationRaw | undefined {
  if (!to.meta.requiresAuth || BILLING_PATHS.some((p) => to.path.startsWith(p))) return
  const subscription = useSubscriptionStore()
  if (!subscription.hasAppAccess && useProfileStore().hasPermission('manage:subscription')) {
    return { path: BILLING_ROUTE }
  }
}
