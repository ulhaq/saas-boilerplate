import { defineStore } from 'pinia'
import { ref } from 'vue'
import { billingApi } from '@/billing/api/billing'
import type { PlanOut, SubscriptionOut, CheckoutOut, CustomerPortalOut } from '@/billing/types'

// Gateway store for the billing domain (see frontend/CLAUDE.md "Data Access").
// Components never import `@/billing/api/billing` directly. Holds derived subscription
// state plus passthrough actions for plan/checkout operations.
export const useSubscriptionStore = defineStore('subscription', () => {
  const subscriptionStatus = ref<string | null>(null)
  const subscriptionTrialEnd = ref<string | null>(null)
  const trialUsed = ref<boolean>(false)
  // Max trial length (days) offered by any active paid plan price. 0 = no trial
  // offered; null = not yet loaded.
  const availableTrialDays = ref<number | null>(null)
  const planFeatures = ref<string[]>([])
  // Plan limit per usage metric (null = unlimited), from GET /billing/usage.
  const usageLimits = ref<Record<string, number | null>>({})
  const seatLimit = computed(() => limitFor('seats'))
  const planSettings = ref<Record<string, number | null>>({})

  // The backend's access policy (`SubscriptionOut.has_access`): whether the
  // subscription's plan applies. Kept server-side so the two can't drift.
  const hasAppAccess = ref(false)

  function limitFor(metric: string): number | null {
    return usageLimits.value[metric] ?? null
  }

  function hasFeature(feature: string): boolean {
    return planFeatures.value.includes(feature)
  }

  async function fetchSubscriptionStatus(): Promise<void> {
    try {
      const { data: subscription } = await billingApi.getCurrentSubscription()
      subscriptionStatus.value = subscription.status
      hasAppAccess.value = subscription.has_access
      subscriptionTrialEnd.value = subscription.trial_end
      trialUsed.value = subscription.trial_used
      planFeatures.value = subscription.features
      planSettings.value = Object.fromEntries(
        subscription.plan_settings.map((s) => [s.key, s.value]),
      )
    } catch {
      subscriptionStatus.value = null
      hasAppAccess.value = false
      subscriptionTrialEnd.value = null
      planFeatures.value = []
      planSettings.value = {}
    }
  }

  async function fetchUsage(): Promise<void> {
    try {
      const { data: usage } = await billingApi.getUsage()
      usageLimits.value = Object.fromEntries(usage.usage.map((u) => [u.metric, u.limit]))
    } catch {
      // non-critical - quota indicator will simply not display
    }
  }

  // Shared in-flight request so concurrent callers on a single page load (e.g.
  // the subscription banner + a billing/landing page) reuse one HTTP request
  // instead of each hitting the plans endpoint.
  let plansInFlight: Promise<PlanOut[]> | null = null

  async function fetchAvailableTrialDays(): Promise<void> {
    try {
      await listPlans()
    } catch {
      availableTrialDays.value = null
    }
  }

  // --- billing passthrough actions (return unwrapped domain data) ---

  async function listPlans(): Promise<PlanOut[]> {
    if (plansInFlight) return plansInFlight
    plansInFlight = billingApi
      .listPlans()
      .then(({ data: plans }) => {
        availableTrialDays.value = plans
          .flatMap((p) => p.prices)
          .filter((price) => price.is_active && price.amount > 0)
          .reduce((max, price) => Math.max(max, price.trial_period_days ?? 0), 0)
        return plans
      })
      .finally(() => {
        plansInFlight = null
      })
    return plansInFlight
  }

  async function getPlan(id: number): Promise<PlanOut> {
    const { data: plan } = await billingApi.getPlan(id)
    return plan
  }

  async function getCurrentSubscription(): Promise<SubscriptionOut> {
    const { data: subscription } = await billingApi.getCurrentSubscription()
    return subscription
  }

  async function startTrial(planPriceId: number): Promise<CheckoutOut> {
    const { data: checkout } = await billingApi.startTrial({ plan_price_id: planPriceId })
    return checkout
  }

  async function checkout(planPriceId: number): Promise<CheckoutOut> {
    const { data: checkoutOut } = await billingApi.checkout({ plan_price_id: planPriceId })
    return checkoutOut
  }

  async function switchPlan(planPriceId: number): Promise<SubscriptionOut> {
    const { data: subscription } = await billingApi.switchPlan({ plan_price_id: planPriceId })
    return subscription
  }

  async function cancelSubscription(): Promise<SubscriptionOut> {
    const { data: subscription } = await billingApi.cancelSubscription()
    return subscription
  }

  async function resumeSubscription(): Promise<SubscriptionOut> {
    const { data: subscription } = await billingApi.resumeSubscription()
    return subscription
  }

  async function updateBillingEmail(billingEmail: string): Promise<SubscriptionOut> {
    const { data: subscription } = await billingApi.updateBillingEmail({
      billing_email: billingEmail,
    })
    return subscription
  }

  async function getPortalUrl(): Promise<CustomerPortalOut> {
    const { data: portal } = await billingApi.getPortalUrl()
    return portal
  }

  function clear(): void {
    subscriptionStatus.value = null
    hasAppAccess.value = false
    subscriptionTrialEnd.value = null
    trialUsed.value = false
    availableTrialDays.value = null
    planFeatures.value = []
    planSettings.value = {}
    usageLimits.value = {}
  }

  return {
    subscriptionStatus,
    subscriptionTrialEnd,
    trialUsed,
    availableTrialDays,
    planFeatures,
    usageLimits,
    seatLimit,
    limitFor,
    planSettings,
    hasAppAccess,
    hasFeature,
    fetchSubscriptionStatus,
    fetchAvailableTrialDays,
    fetchUsage,
    listPlans,
    getPlan,
    getCurrentSubscription,
    startTrial,
    checkout,
    switchPlan,
    cancelSubscription,
    resumeSubscription,
    updateBillingEmail,
    getPortalUrl,
    clear,
  }
})
