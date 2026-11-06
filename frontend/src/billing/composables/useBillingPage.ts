import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { rememberCurrency, rememberedCurrency } from '@/billing/currency'
import { useSubscriptionStore } from '@/billing/stores/subscription'
import { useConfirm } from '@/foundation/composables/useConfirm'
import { useToast } from '@/foundation/composables/useToast'
import { useErrorHandler } from '@/foundation/composables/useErrorHandler'
import { useSaveFeedback } from '@/foundation/composables/useSaveFeedback'
import type { ComparisonRow } from '@/billing/composables/useBillingFormat'
import type { SubscriptionOut, PlanOut, PlanPriceOut } from '@/billing/types'

/** State and actions of the billing settings page (`pages/settings/billing.vue`). */
export function useBillingPage() {
  const subscriptionStore = useSubscriptionStore()
  const { t, tm, locale } = useI18n()
  const { toast } = useToast()
  const { confirm } = useConfirm()
  const { resolveError } = useErrorHandler()

  const isLoading = ref(false)
  const plansLoading = ref(false)
  const isActing = ref(false)
  const isPortalLoading = ref(false)
  const checkoutId = ref<number | undefined>(undefined)
  const isCheckingOut = ref(false)
  const isTrialing = ref(false)
  const trialId = ref<number | undefined>(undefined)
  const switchId = ref<number | undefined>(undefined)
  const { saving: emailSaving, saved: emailSaved, save: saveEmail } = useSaveFeedback()
  const billingEmail = ref('')
  const subscription = ref<SubscriptionOut | null>(null)
  const plans = ref<PlanOut[]>([])
  const errorMessage = ref('')

  /** The currencies the paid plans are priced in. */
  const currencies = computed(() =>
    [
      ...new Set(
        plans.value
          .flatMap((p) => p.prices)
          .filter((pr) => pr.is_active && pr.amount > 0)
          .map((pr) => pr.currency),
      ),
    ].sort(),
  )

  /** A paid subscription's currency: Stripe bills a subscription in one currency, so the
   * plans to switch to are offered in it, and no other can be picked. */
  const lockedCurrency = computed(() => {
    const current = subscription.value?.plan_price
    return current && current.amount > 0 ? current.currency : null
  })

  /** The currency the user picked, here or on the marketing site, remembered in this browser. */
  const chosenCurrency = ref<string | null>(rememberedCurrency())

  /** The currency the page offers: the paid subscription's, else the one picked, else the
   * locale's, else EUR - whichever the paid plans are priced in. */
  const currency = computed(() => {
    if (lockedCurrency.value) return lockedCurrency.value
    const offered = currencies.value
    if (chosenCurrency.value && offered.includes(chosenCurrency.value)) return chosenCurrency.value
    const preferred = locale.value.startsWith('da') ? 'dkk' : 'eur'
    if (offered.includes(preferred)) return preferred
    return offered.includes('eur') ? 'eur' : (offered[0] ?? preferred)
  })

  /** The currencies the user may pick from: none while a paid subscription fixes it. */
  const currencyChoices = computed(() => (lockedCurrency.value ? [] : currencies.value))

  function setCurrency(value: string) {
    chosenCurrency.value = value
    rememberCurrency(value)
  }

  /** Active plans with only their prices in `currency` (a free price in any), cheapest first. */
  const availablePlans = computed<PlanOut[]>(() =>
    plans.value
      .map((plan) => ({
        ...plan,
        prices: plan.prices.filter((pr) => pr.amount === 0 || pr.currency === currency.value),
      }))
      .sort((a, b) => minPrice(a) - minPrice(b)),
  )

  function minPrice(plan: PlanOut): number {
    return Math.min(...plan.prices.filter((p) => p.is_active).map((p) => p.amount), Infinity)
  }

  const trialPrice = computed<PlanPriceOut | undefined>(() => {
    const last = availablePlans.value[availablePlans.value.length - 1]
    if (!last) return undefined
    for (const price of last.prices) {
      if (price.is_active && price.amount > 0 && price.trial_period_days) {
        return price
      }
    }
    return undefined
  })

  const paidPlans = computed(() =>
    availablePlans.value.filter((p) => p.prices.some((pr) => pr.is_active && pr.amount > 0)),
  )

  const comparisonRows = computed(() => (tm('planComparisonRows') as ComparisonRow[]) ?? [])

  function planName(price: PlanPriceOut | null): string {
    if (!price) return ''
    const plan = availablePlans.value.find((p) => p.prices.some((pr) => pr.id === price.id))
    return plan?.name ?? ''
  }

  async function loadSubscription() {
    isLoading.value = true
    try {
      const data = await subscriptionStore.getCurrentSubscription()
      subscription.value = data
      billingEmail.value = data.billing_email ?? ''
      subscriptionStore.subscriptionStatus = data.status
      subscriptionStore.subscriptionTrialEnd = data.trial_end
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status !== 404) {
        errorMessage.value = resolveError(err)
      }
    } finally {
      isLoading.value = false
    }
  }

  function onVisibilityChange() {
    if (document.visibilityState === 'visible') {
      loadSubscription()
    }
  }

  onMounted(async () => {
    await loadSubscription()

    plansLoading.value = true
    try {
      const data = await subscriptionStore.listPlans()
      plans.value = data.filter((p) => p.is_active)
    } catch {
      // Non-critical - plan list is optional context
    } finally {
      plansLoading.value = false
    }

    document.addEventListener('visibilitychange', onVisibilityChange)
  })

  onUnmounted(() => {
    document.removeEventListener('visibilitychange', onVisibilityChange)
  })

  async function handleCancel() {
    const ok = await confirm(
      t('subscription.cancelTitle'),
      t('subscription.cancelDescription'),
      t('subscription.cancelConfirm'),
    )
    if (!ok) return
    isActing.value = true
    try {
      const data = await subscriptionStore.cancelSubscription()
      subscription.value = data
      toast({ title: t('subscription.cancelScheduledSuccess') })
    } catch (err: unknown) {
      toast({ title: resolveError(err), variant: 'destructive' })
    } finally {
      isActing.value = false
    }
  }

  async function handleResume() {
    isActing.value = true
    try {
      const data = await subscriptionStore.resumeSubscription()
      subscription.value = data
      toast({ title: t('subscription.resumed') })
    } catch (err: unknown) {
      toast({ title: resolveError(err), variant: 'destructive' })
    } finally {
      isActing.value = false
    }
  }

  async function handlePortal() {
    isPortalLoading.value = true
    try {
      const data = await subscriptionStore.getPortalUrl()
      const parsed = new URL(data.portal_url)
      if (!['https:', 'http:'].includes(parsed.protocol)) throw new Error('Invalid URL protocol')
      window.open(data.portal_url, '_blank', 'noopener,noreferrer')
    } catch (err: unknown) {
      toast({ title: resolveError(err), variant: 'destructive' })
    } finally {
      isPortalLoading.value = false
    }
  }

  async function handleSwitchPlan(priceId: number, priceAmount: number) {
    const currentAmount = subscription.value?.plan_price?.amount ?? 0
    const isUpgrade = priceAmount > currentAmount
    const ok = await confirm(
      t('subscription.switchPlanTitle'),
      t('subscription.switchPlanDescription'),
      t(isUpgrade ? 'subscription.upgrade' : 'subscription.downgrade'),
      isUpgrade ? 'default' : 'destructive',
    )
    if (!ok) return
    switchId.value = priceId
    try {
      const data = await subscriptionStore.switchPlan(priceId)
      subscription.value = data
      subscriptionStore.subscriptionStatus = data.status
      subscriptionStore.subscriptionTrialEnd = data.trial_end
      toast({ title: t('subscription.switchPlanSuccess') })
      switchId.value = undefined
    } catch (err: unknown) {
      toast({ title: resolveError(err), variant: 'destructive' })
      switchId.value = undefined
    }
  }

  async function handleTrial(priceId: number) {
    trialId.value = priceId
    isTrialing.value = true
    try {
      const data = await subscriptionStore.startTrial(priceId)
      window.location.href = data.checkout_url
    } catch (err: unknown) {
      toast({ title: resolveError(err), variant: 'destructive' })
      trialId.value = undefined
      isTrialing.value = false
    }
  }

  async function handleSaveEmail() {
    try {
      const data = await saveEmail(() =>
        subscriptionStore.updateBillingEmail(billingEmail.value.trim()),
      )
      subscription.value = data
      billingEmail.value = data.billing_email ?? ''
    } catch (err: unknown) {
      toast({ title: resolveError(err), variant: 'destructive' })
    }
  }

  async function handleCheckout(priceId: number) {
    checkoutId.value = priceId
    isCheckingOut.value = true
    try {
      const data = await subscriptionStore.checkout(priceId)
      window.location.href = data.checkout_url
    } catch (err: unknown) {
      toast({ title: resolveError(err), variant: 'destructive' })
      checkoutId.value = undefined
      isCheckingOut.value = false
    }
  }

  return {
    isLoading,
    plansLoading,
    isActing,
    isPortalLoading,
    checkoutId,
    isCheckingOut,
    isTrialing,
    trialId,
    switchId,
    emailSaving,
    emailSaved,
    billingEmail,
    subscription,
    availablePlans,
    errorMessage,
    trialPrice,
    paidPlans,
    currency,
    currencyChoices,
    setCurrency,
    comparisonRows,
    planName,
    handleCancel,
    handleResume,
    handlePortal,
    handleSwitchPlan,
    handleTrial,
    handleSaveEmail,
    handleCheckout,
  }
}
