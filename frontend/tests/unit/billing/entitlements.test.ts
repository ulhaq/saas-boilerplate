import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, test } from 'vitest'
import type { RouteLocationNormalized } from 'vue-router'
import { BILLING_ROUTE, requireAppAccess, useBillingEntitlements } from '@/billing/entitlements'
import { useSubscriptionStore } from '@/billing/stores/subscription'
import { useProfileStore } from '@/platform/stores/profile'
import { i18n } from '@/plugins/i18n'

const route = (path: string, requiresAuth = true) =>
  ({ path, meta: { requiresAuth } }) as unknown as RouteLocationNormalized

let subscription: ReturnType<typeof useSubscriptionStore>

beforeEach(() => {
  setActivePinia(createPinia())
  subscription = useSubscriptionStore()
  useProfileStore().permissions = ['manage:subscription']
})

describe('billing entitlements', () => {
  test('report the plan features and limits from the subscription store', () => {
    subscription.planFeatures = ['api_token']
    subscription.usageLimits = { seats: 3, projects: null }
    const entitlements = useBillingEntitlements()

    expect(entitlements.hasFeature('api_token')).toBe(true)
    expect(entitlements.hasFeature('sso')).toBe(false)
    expect(entitlements.limitFor('seats')).toBe(3)
    expect(entitlements.limitFor('projects')).toBeNull()

    entitlements.clear()
    expect(entitlements.hasFeature('api_token')).toBe(false)
  })
})

describe('app access guard', () => {
  test('sends an organization without a usable subscription to the billing page', () => {
    subscription.subscriptionStatus = 'canceled'

    expect(requireAppAccess(route('/projects'))).toEqual({ path: BILLING_ROUTE })
    // Not from billing's own pages, nor from public ones.
    expect(requireAppAccess(route(BILLING_ROUTE))).toBeUndefined()
    expect(requireAppAccess(route('/billing/success'))).toBeUndefined()
    expect(requireAppAccess(route('/login', false))).toBeUndefined()
  })

  test('lets active, trialing and past-due organizations in', () => {
    for (const status of ['active', 'trialing', 'past_due']) {
      subscription.subscriptionStatus = status
      expect(requireAppAccess(route('/projects')), status).toBeUndefined()
    }
  })

  test('does not redirect users who cannot manage the subscription', () => {
    subscription.subscriptionStatus = 'canceled'
    useProfileStore().permissions = []

    expect(requireAppAccess(route('/projects'))).toBeUndefined()
  })
})

describe('plan summary', () => {
  test('shows the subscription status, linking managers to the billing page', () => {
    subscription.subscriptionStatus = 'trialing'
    const { t } = i18n.global

    expect(useBillingEntitlements().planSummary()).toEqual({
      label: t('subscription.status.trialing'),
      route: BILLING_ROUTE,
    })

    useProfileStore().permissions = []
    expect(useBillingEntitlements().planSummary()?.route).toBeNull()
  })
})
