import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import Billing from '@/platform/pages/settings/billing.vue'
import { i18n } from '@/plugins/i18n'
import { useSubscriptionStore } from '@/platform/stores/subscription'
import type { PlanOut, PlanPriceOut, SubscriptionOut } from '@/platform/types'

const t = i18n.global.t

const confirm = vi.fn(async (..._args: unknown[]) => true)
const toast = vi.fn()
vi.mock('@/platform/composables/useConfirm', () => ({ useConfirm: () => ({ confirm }) }))
vi.mock('@/platform/composables/useToast', () => ({ useToast: () => ({ toast }) }))

function price(id: number, amount: number, interval: string, trial: number | null): PlanPriceOut {
  return {
    id,
    plan_id: id,
    amount,
    currency: 'dkk',
    interval,
    interval_count: 1,
    trial_period_days: trial,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

const FREE = price(1, 0, 'month', null)
const PRO_MONTHLY = price(2, 9900, 'month', 14)
const PRO_YEARLY = price(3, 99000, 'year', 14)
const BUSINESS = price(4, 29900, 'month', null)

function plan(id: number, name: string, prices: PlanPriceOut[]): PlanOut {
  return {
    id,
    name,
    description: null,
    is_active: true,
    prices,
    plan_settings: [],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

const PLANS = [
  plan(1, 'Free', [FREE]),
  plan(2, 'Pro', [PRO_MONTHLY, PRO_YEARLY]),
  plan(3, 'Business', [BUSINESS]),
]

function subscription(overrides: Partial<SubscriptionOut> = {}): SubscriptionOut {
  return {
    id: 10,
    organization_id: 1,
    plan_price_id: PRO_MONTHLY.id,
    status: 'active',
    current_period_start: '2026-09-01T00:00:00Z',
    current_period_end: '2026-10-01T00:00:00Z',
    cancel_at_period_end: false,
    canceled_at: null,
    cancel_at: null,
    trial_end: null,
    plan_price: PRO_MONTHLY,
    billing_email: 'billing@acme.dk',
    has_payment_method: true,
    trial_used: false,
    features: [],
    plan_settings: [],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

const onFreePlan = (overrides: Partial<SubscriptionOut> = {}) =>
  subscription({ plan_price_id: FREE.id, plan_price: FREE, ...overrides })

let store: ReturnType<typeof useSubscriptionStore>

/** Mount the page for a subscription (`null`: the organization has none). */
async function mountBilling(
  current: SubscriptionOut | null,
  plans: PlanOut[] = PLANS,
): Promise<VueWrapper> {
  setActivePinia(createPinia())
  store = useSubscriptionStore()
  store.getCurrentSubscription = vi.fn(async () => {
    if (!current) throw { response: { status: 404 } }
    return current
  })
  store.listPlans = vi.fn(async () => plans)
  store.checkout = vi.fn(async () => ({ checkout_url: 'https://checkout.test/session' }))
  store.startTrial = vi.fn(async () => ({ checkout_url: 'https://checkout.test/trial' }))
  store.getPortalUrl = vi.fn(async () => ({ portal_url: 'https://portal.test/session' }))
  store.switchPlan = vi.fn(async () => subscription())
  store.cancelSubscription = vi.fn(async () => subscription({ cancel_at_period_end: true }))
  store.resumeSubscription = vi.fn(async () => subscription())
  store.updateBillingEmail = vi.fn(async (email: string) => subscription({ billing_email: email }))
  const wrapper = mount(Billing, { global: { plugins: [i18n] } })
  await flushPromises()
  return wrapper
}

const buttonLabels = (wrapper: VueWrapper) =>
  wrapper
    .findAll('button')
    .map((b) => b.text().trim())
    .filter(Boolean)

function buttons(wrapper: VueWrapper, label: string) {
  return wrapper.findAll('button').filter((b) => b.text().trim() === label)
}

async function click(wrapper: VueWrapper, label: string, index = 0) {
  const button = buttons(wrapper, label)[index]
  expect(button, `button "${label}" #${index}`).toBeDefined()
  await button!.trigger('click')
  await flushPromises()
}

beforeEach(() => {
  i18n.global.locale.value = 'en'
  confirm.mockClear()
  toast.mockClear()
  vi.spyOn(window, 'open').mockImplementation(() => null)
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('billing page', () => {
  test('without a subscription, every active price can be subscribed to via checkout', async () => {
    const wrapper = await mountBilling(null)

    expect(wrapper.text()).toContain(t('subscription.noSubscription'))
    expect(buttons(wrapper, t('subscription.subscribe'))).toHaveLength(4)

    await click(wrapper, t('subscription.subscribe'), 1)
    expect(store.checkout).toHaveBeenCalledWith(PRO_MONTHLY.id)
  })

  test('an incomplete subscription resumes checkout for its pending price', async () => {
    const wrapper = await mountBilling(subscription({ status: 'incomplete' }))

    await click(wrapper, t('subscription.subscribe'))
    expect(store.checkout).toHaveBeenCalledWith(PRO_MONTHLY.id)
  })

  test('a free user with a trial left can start a trial, or subscribe to plans without one', async () => {
    const wrapper = await mountBilling(onFreePlan())

    expect(wrapper.text()).toContain(t('subscription.noCardRequired'))
    // One trial button per trial-eligible price: Pro monthly, then Pro yearly.
    expect(buttons(wrapper, t('subscription.startTrialButton', { days: 14 }))).toHaveLength(2)
    await click(wrapper, t('subscription.startTrialButton', { days: 14 }), 1)
    expect(store.startTrial).toHaveBeenCalledWith(PRO_YEARLY.id)

    await click(wrapper, t('subscription.subscribe'))
    expect(store.checkout).toHaveBeenCalledWith(BUSINESS.id)
    expect(store.switchPlan).not.toHaveBeenCalled()
  })

  test('a free user who used their trial subscribes through checkout only', async () => {
    const wrapper = await mountBilling(onFreePlan({ trial_used: true }))

    expect(buttonLabels(wrapper)).not.toContain(t('subscription.startTrialButton', { days: 14 }))
    expect(buttons(wrapper, t('subscription.subscribe'))).toHaveLength(3)

    await click(wrapper, t('subscription.subscribe'), 2)
    expect(store.checkout).toHaveBeenCalledWith(BUSINESS.id)
  })

  test('a paused subscription can add a payment method or switch to another plan', async () => {
    const wrapper = await mountBilling(
      subscription({ status: 'paused', has_payment_method: false }),
    )

    await click(wrapper, t('subscription.addPaymentMethod'))
    expect(window.open).toHaveBeenCalledWith(
      'https://portal.test/session',
      '_blank',
      'noopener,noreferrer',
    )

    const current = buttons(wrapper, t('subscription.currentPlan'))
    expect(current).toHaveLength(1)
    expect(current[0]!.attributes('disabled')).toBeDefined()

    await click(wrapper, t('subscription.subscribe'), 1)
    expect(confirm).toHaveBeenCalledOnce()
    expect(store.switchPlan).toHaveBeenCalledWith(BUSINESS.id)
  })

  test('an active subscription labels other plans by monthly price and switches after confirmation', async () => {
    const wrapper = await mountBilling(subscription())

    // Yearly Pro (825/month) is cheaper per month than monthly Pro (990).
    expect(buttonLabels(wrapper)).toEqual(
      expect.arrayContaining([
        t('subscription.currentPlan'),
        t('subscription.downgrade'),
        t('subscription.upgrade'),
      ]),
    )

    await click(wrapper, t('subscription.upgrade'))
    expect(confirm).toHaveBeenCalledWith(
      t('subscription.switchPlanTitle'),
      expect.any(String),
      t('subscription.upgrade'),
      'default',
    )
    expect(store.switchPlan).toHaveBeenCalledWith(BUSINESS.id)
    expect(toast).toHaveBeenCalledWith({ title: t('subscription.switchPlanSuccess') })
  })

  test('cancelling asks for confirmation, then schedules the cancellation', async () => {
    const wrapper = await mountBilling(subscription())

    await click(wrapper, t('subscription.cancelSubscription'))
    expect(confirm).toHaveBeenCalledOnce()
    expect(store.cancelSubscription).toHaveBeenCalledOnce()
    expect(buttonLabels(wrapper)).toContain(t('subscription.resumeSubscription'))
  })

  test('a pending cancellation can be resumed and cannot be cancelled again', async () => {
    const wrapper = await mountBilling(subscription({ cancel_at_period_end: true }))

    expect(buttonLabels(wrapper)).not.toContain(t('subscription.cancelSubscription'))
    await click(wrapper, t('subscription.resumeSubscription'))
    expect(store.resumeSubscription).toHaveBeenCalledOnce()
  })

  test('a trial without a card on file prompts for a payment method', async () => {
    const wrapper = await mountBilling(
      subscription({
        status: 'trialing',
        trial_end: '2026-10-15T12:00:00Z',
        has_payment_method: false,
      }),
    )

    expect(wrapper.find('.text-warning').text()).toContain('Oct 15, 2026')
    await click(wrapper, t('subscription.addPaymentMethod'))
    expect(window.open).toHaveBeenCalledOnce()
  })

  test('the billing email saves only once it changes', async () => {
    const wrapper = await mountBilling(subscription())
    const save = () => buttons(wrapper, t('subscription.billingEmailSave'))[0]!

    expect(save().attributes('disabled')).toBeDefined()
    await wrapper.find('#billing-email').setValue('finance@acme.dk')
    expect(save().attributes('disabled')).toBeUndefined()

    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(store.updateBillingEmail).toHaveBeenCalledWith('finance@acme.dk')
  })

  test('a failed checkout shows the error and re-enables the button', async () => {
    const wrapper = await mountBilling(null)
    store.checkout = vi.fn(async () => {
      throw new Error('boom')
    })

    await click(wrapper, t('subscription.subscribe'))
    expect(toast).toHaveBeenCalledWith(expect.objectContaining({ variant: 'destructive' }))
    expect(buttons(wrapper, t('subscription.subscribe'))[0]!.attributes('disabled')).toBeUndefined()
  })

  test('a failure to load the subscription other than 404 is shown', async () => {
    setActivePinia(createPinia())
    store = useSubscriptionStore()
    store.getCurrentSubscription = vi.fn(async () => {
      throw new Error('network down')
    })
    store.listPlans = vi.fn(async () => PLANS)
    const wrapper = mount(Billing, { global: { plugins: [i18n] } })
    await flushPromises()

    expect(wrapper.find('.text-destructive').exists()).toBe(true)
  })
})

describe('plan descriptions', () => {
  // Paid plans without a trial, so every section lists all three.
  const PLANS_TO_DESCRIBE = [
    plan(1, 'Free', [FREE]),
    plan(5, 'Localized', [price(5, 5000, 'month', null)]),
    { ...plan(6, 'Described', [price(6, 6000, 'month', null)]), description: 'Own text' },
    plan(7, 'Bare', [price(7, 7000, 'month', null)]),
  ]

  beforeEach(() => {
    i18n.global.mergeLocaleMessage('en', { planDescriptions: { Localized: 'Locale text' } })
  })

  test.each([
    ['free plan', onFreePlan({ trial_used: true })],
    ['active subscription', subscription()],
    ['no subscription', null],
  ])('on the %s, use the locale text, else the plan text, else nothing', async (_, current) => {
    const wrapper = await mountBilling(current, PLANS_TO_DESCRIBE)
    const text = wrapper.text()

    expect(text).toContain('Locale text')
    expect(text).toContain('Own text')
    expect(text).not.toContain('planDescriptions.')
  })
})
