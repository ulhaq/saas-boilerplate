/**
 * Billing module entry - plans, subscriptions and Stripe checkout, plugged into
 * the foundation shell like a product (the frontend twin of the backend's
 * `src/billing/module.py`). Listed in `src/products.ts`; drop it there (and
 * from `products.config.js`) to run without plans: every feature on, no limits.
 */
import { Receipt } from 'lucide-vue-next'
import SubscriptionBanner from '@/billing/components/SubscriptionBanner.vue'
import { BILLING_ROUTE, requireAppAccess, useBillingEntitlements } from '@/billing/entitlements'
import da from '@/billing/locales/da'
import en from '@/billing/locales/en'
import { registerBillingNotifications } from '@/billing/notifications'
import { registerBanner } from '@/foundation/banners'
import { configureApp } from '@/foundation/config'
import { provideEntitlements } from '@/foundation/entitlements'
import { registerSettingsNavItems } from '@/foundation/navigation'
import type { Module } from '@/foundation/module'
import { registerRouteGuard } from '@/foundation/routeGuards'

const billing: Module = {
  name: 'billing',
  messages: { da, en },
  setup() {
    provideEntitlements(useBillingEntitlements)
    registerRouteGuard(requireAppAccess)
    registerBanner(SubscriptionBanner)
    registerSettingsNavItems('organization', [
      {
        to: BILLING_ROUTE,
        labelKey: 'nav.subscription',
        icon: Receipt,
        order: 10,
        permission: 'manage:subscription',
      },
    ])
    // New accounts pick a plan first; upgrade prompts link to the plans.
    configureApp({ upgradeRoute: BILLING_ROUTE, onboardingRoute: BILLING_ROUTE })
    registerBillingNotifications()
  },
}

export default billing
