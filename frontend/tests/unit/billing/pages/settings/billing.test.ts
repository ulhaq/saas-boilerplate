import { enableAutoUnmount, flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import Billing from '@/billing/pages/settings/billing.vue'
import { i18n } from '@/plugins/i18n'
import { adoptPlanChoiceFromUrl } from '@/billing/currency'
import { useSubscriptionStore } from '@/billing/stores/subscription'
import type { PlanOut, PlanPriceOut, SubscriptionOut } from '@/billing/types'

const t = i18n.global.t

/** A price as the page writes it: whole amounts without decimals. */
const money = (amount: number, currency: string) =>
  new Intl.NumberFormat('en', {
    style: 'currency',
    currency,
    minimumFractionDigits: Number.isInteger(amount) ? 0 : 2,
    maximumFractionDigits: Number.isInteger(amount) ? 0 : 2,
  }).format(amount)

const confirm = vi.fn(async (..._args: unknown[]) => true)
const toast = vi.fn()
vi.mock('@/foundation/composables/useConfirm', () => ({ useConfirm: () => ({ confirm }) }))
vi.mock('@/foundation/composables/useToast', () => ({ useToast: () => ({ toast }) }))

function price(
  id: number,
  amount: number,
  interval: string,
  trial: number | null,
  currency = 'dkk',
): PlanPriceOut {
  return {
    id,
    plan_id: id,
    amount,
    currency,
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
// Pro's second price: same plan as monthly Pro.
const PRO_YEARLY = { ...price(3, 99000, 'year', 14), plan_id: PRO_MONTHLY.plan_id }
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
    has_access: true,
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

/** The options of the radio group labelled `label` (the currency or billing period). */
const options = (wrapper: VueWrapper, label: string) =>
  wrapper.findAll(`[role="radiogroup"][aria-label="${label}"] [role="radio"]`)

async function pickInterval(wrapper: VueWrapper, interval: 'month' | 'year') {
  const option = options(wrapper, t('subscription.billingInterval')).find((o) =>
    o.text().startsWith(t(`subscription.intervalOptions.${interval}`)),
  )
  expect(option, `interval option ${interval}`).toBeDefined()
  await option!.trigger('click')
  await flushPromises()
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
  localStorage.clear()
  confirm.mockClear()
  toast.mockClear()
  vi.spyOn(window, 'open').mockImplementation(() => null)
})

// Unmount each test's page, so earlier ones don't keep rendering (and slowing) later ones.
enableAutoUnmount(afterEach)

afterEach(() => {
  vi.restoreAllMocks()
})

describe('billing page', () => {
  test('without a subscription, every monthly price can be subscribed to via checkout', async () => {
    const wrapper = await mountBilling(null)

    expect(wrapper.text()).toContain(t('subscription.noSubscription'))
    // Free, Pro monthly and Business: yearly prices wait behind the toggle.
    expect(buttons(wrapper, t('subscription.subscribe'))).toHaveLength(3)

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
    // One trial button per trial-eligible price in the period shown: Pro monthly.
    expect(buttons(wrapper, t('subscription.startTrialButton', { days: 14 }))).toHaveLength(1)
    await click(wrapper, t('subscription.subscribe'))
    expect(store.checkout).toHaveBeenCalledWith(BUSINESS.id)

    await pickInterval(wrapper, 'year')
    await click(wrapper, t('subscription.startTrialButton', { days: 14 }))
    expect(store.startTrial).toHaveBeenCalledWith(PRO_YEARLY.id)
    expect(store.switchPlan).not.toHaveBeenCalled()
  })

  test('a free user who used their trial subscribes through checkout only', async () => {
    const wrapper = await mountBilling(onFreePlan({ trial_used: true }))

    expect(buttonLabels(wrapper)).not.toContain(t('subscription.startTrialButton', { days: 14 }))
    expect(buttons(wrapper, t('subscription.subscribe'))).toHaveLength(2)

    await click(wrapper, t('subscription.subscribe'), 1)
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

    await click(wrapper, t('subscription.subscribe'))
    expect(confirm).toHaveBeenCalledOnce()
    expect(store.switchPlan).toHaveBeenCalledWith(BUSINESS.id)
  })

  test('an active subscription labels other plans by monthly price and switches after confirmation', async () => {
    const wrapper = await mountBilling(subscription())

    expect(buttonLabels(wrapper)).toEqual(
      expect.arrayContaining([t('subscription.currentPlan'), t('subscription.upgrade')]),
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

describe('currencies', () => {
  const FREE_EUR = price(20, 0, 'month', null, 'eur')
  const BASIC_EUR = price(21, 1200, 'month', null, 'eur')
  const BASIC_DKK = price(22, 8900, 'month', null, 'dkk')
  const PLANS_IN_TWO = [plan(1, 'Free', [FREE_EUR]), plan(2, 'Basic', [BASIC_EUR, BASIC_DKK])]

  test.each([
    ['da', BASIC_DKK],
    ['en', BASIC_EUR],
  ])('without a subscription, the %s locale is offered its currency only', async (lang, paid) => {
    i18n.global.locale.value = lang as 'en' | 'da'
    const wrapper = await mountBilling(null, PLANS_IN_TWO)

    // The free price and one paid price, not both currencies.
    expect(buttons(wrapper, t('subscription.subscribe'))).toHaveLength(2)
    await click(wrapper, t('subscription.subscribe'), 1)
    expect(store.checkout).toHaveBeenCalledWith(paid.id)
  })

  test('a paid subscription keeps its currency, whatever the locale', async () => {
    i18n.global.locale.value = 'da'
    const wrapper = await mountBilling(
      subscription({ plan_price_id: BASIC_EUR.id, plan_price: BASIC_EUR }),
      [
        ...PLANS_IN_TWO,
        plan(3, 'Pro', [
          price(23, 3900, 'month', null, 'eur'),
          price(24, 29000, 'month', null, 'dkk'),
        ]),
      ],
    )

    await click(wrapper, t('subscription.upgrade'))
    expect(store.switchPlan).toHaveBeenCalledWith(23)
  })

  const currencyOptions = (wrapper: VueWrapper) => options(wrapper, t('subscription.currency'))

  test('a picked currency is offered instead of the locale one, and remembered', async () => {
    const wrapper = await mountBilling(null, PLANS_IN_TWO)

    expect(currencyOptions(wrapper).map((o) => o.text())).toEqual(['DKK', 'EUR'])
    expect(currencyOptions(wrapper)[1]!.attributes('aria-checked')).toBe('true')
    await currencyOptions(wrapper)[0]!.trigger('click')
    await click(wrapper, t('subscription.subscribe'), 1)
    expect(store.checkout).toHaveBeenCalledWith(BASIC_DKK.id)

    // Back on the page later, the choice still holds.
    const again = await mountBilling(null, PLANS_IN_TWO)
    await click(again, t('subscription.subscribe'), 1)
    expect(store.checkout).toHaveBeenCalledWith(BASIC_DKK.id)
  })

  test('the currency picked on the marketing site is offered', async () => {
    window.history.replaceState(null, '', '/settings/billing?currency=dkk')
    adoptPlanChoiceFromUrl()
    const wrapper = await mountBilling(null, PLANS_IN_TWO)

    await click(wrapper, t('subscription.subscribe'), 1)
    expect(store.checkout).toHaveBeenCalledWith(BASIC_DKK.id)
  })

  test('a free user can pick the currency too', async () => {
    const wrapper = await mountBilling(
      onFreePlan({ plan_price: FREE_EUR, plan_price_id: FREE_EUR.id }),
      PLANS_IN_TWO,
    )

    await currencyOptions(wrapper)[0]!.trigger('click')
    await click(wrapper, t('subscription.subscribe'))
    expect(store.checkout).toHaveBeenCalledWith(BASIC_DKK.id)
  })

  test("the free plan's price follows the picked currency", async () => {
    const wrapper = await mountBilling(
      onFreePlan({ plan_price: FREE_EUR, plan_price_id: FREE_EUR.id }),
      PLANS_IN_TWO,
    )
    const zero = (currency: string) => money(0, currency)

    expect(wrapper.text()).toContain(zero('eur'))
    await currencyOptions(wrapper)[0]!.trigger('click')
    expect(wrapper.text()).toContain(zero('dkk'))
    expect(wrapper.text()).not.toContain(zero('eur'))
  })

  test('a paid subscription offers no currency to pick', async () => {
    const wrapper = await mountBilling(
      subscription({ plan_price_id: BASIC_EUR.id, plan_price: BASIC_EUR }),
      PLANS_IN_TWO,
    )

    expect(currencyOptions(wrapper)).toHaveLength(0)
  })

  test('with one currency, there is nothing to pick', async () => {
    const wrapper = await mountBilling(null)

    expect(currencyOptions(wrapper)).toHaveLength(0)
  })

  test('a locale whose currency no plan is priced in falls back to EUR', async () => {
    i18n.global.locale.value = 'da'
    const wrapper = await mountBilling(null, [
      plan(1, 'Free', [FREE_EUR]),
      plan(2, 'Basic', [BASIC_EUR, price(25, 1300, 'month', null, 'usd')]),
    ])

    await click(wrapper, t('subscription.subscribe'), 1)
    expect(store.checkout).toHaveBeenCalledWith(BASIC_EUR.id)
  })
})

describe('billing periods', () => {
  const intervalOptions = (wrapper: VueWrapper) =>
    options(wrapper, t('subscription.billingInterval'))

  test('monthly is shown first, with the months yearly gives free', async () => {
    const wrapper = await mountBilling(null)
    // Monthly prices save nothing, so no card says so.
    expect(wrapper.text()).not.toContain(
      t('subscription.yearlySavingAmount', { amount: money(198, 'dkk') }),
    )

    const labels = intervalOptions(wrapper).map((o) => o.text().replace(/\s+/g, ' '))
    // 99000 a year against 12 x 9900: 10 months' worth, so 2 months free.
    expect(labels).toEqual([
      t('subscription.intervalOptions.month'),
      `${t('subscription.intervalOptions.year')} ${t('subscription.monthsFree', { count: 2 }, 2)}`,
    ])
    expect(intervalOptions(wrapper)[0]!.attributes('aria-checked')).toBe('true')
    expect(wrapper.text()).toContain(t('subscription.billed.month'))
  })

  test('a yearly price that is no whole number of months is shown as a percentage', async () => {
    const wrapper = await mountBilling(null, [
      plan(1, 'Free', [FREE]),
      plan(2, 'Pro', [PRO_MONTHLY, { ...PRO_YEARLY, amount: 95000 }]),
    ])

    // 95000 against 12 x 9900 = 118800: 20% less.
    expect(intervalOptions(wrapper)[1]!.text()).toContain(
      t('subscription.yearlySaving', { percent: 20 }),
    )
  })

  test('the saving shown is the smallest of the plans', async () => {
    const wrapper = await mountBilling(null, [
      plan(1, 'Free', [FREE]),
      plan(2, 'Pro', [PRO_MONTHLY, { ...PRO_YEARLY, amount: 95000 }]),
      plan(3, 'Business', [
        price(30, 20000, 'month', null, 'dkk'),
        price(31, 180000, 'year', null, 'dkk'),
      ]),
    ])

    // Pro saves 20% (95000 against 118800), Business 25% (180000 against 240000).
    expect(intervalOptions(wrapper)[1]!.text()).toContain(
      t('subscription.yearlySaving', { percent: 20 }),
    )
  })

  test('picking yearly offers the yearly prices, by the month, billed yearly', async () => {
    const wrapper = await mountBilling(null)
    const dkk = (amount: number) => money(amount, 'dkk')

    await pickInterval(wrapper, 'year')
    // Free and Pro yearly; Business has no yearly price.
    expect(buttons(wrapper, t('subscription.subscribe'))).toHaveLength(2)
    expect(wrapper.text()).toContain(`${dkk(82.5)} / ${t('subscription.intervals.month')}`)
    expect(wrapper.text()).toContain(t('subscription.billed.year'))
    expect(wrapper.text()).not.toContain(t('subscription.billed.month'))
    // The yearly total is not shown, only the period it is billed in.
    expect(wrapper.text()).not.toContain(dkk(990))
    expect(wrapper.text()).not.toContain(`/ ${t('subscription.intervals.year')}`)
    // 12 x 99 - 990: what the yearly price saves on the plan's card.
    expect(wrapper.text()).toContain(t('subscription.yearlySavingAmount', { amount: dkk(198) }))
    await click(wrapper, t('subscription.subscribe'), 1)
    expect(store.checkout).toHaveBeenCalledWith(PRO_YEARLY.id)
  })

  test('a yearly subscription is shown its own period, and can move to monthly', async () => {
    const wrapper = await mountBilling(
      subscription({ plan_price_id: PRO_YEARLY.id, plan_price: PRO_YEARLY }),
    )

    expect(intervalOptions(wrapper)[1]!.attributes('aria-checked')).toBe('true')
    expect(buttonLabels(wrapper)).toContain(t('subscription.currentPlan'))
    // The current price too: by the month, billed yearly.
    expect(wrapper.text()).toContain(t('subscription.billed.year'))

    await pickInterval(wrapper, 'month')
    await click(wrapper, t('subscription.switchInterval.month'))
    expect(confirm).toHaveBeenCalledWith(
      t('subscription.switchPlanTitle'),
      expect.any(String),
      t('subscription.switchInterval.month'),
      'default',
    )
    expect(store.switchPlan).toHaveBeenCalledWith(PRO_MONTHLY.id)
  })

  test('a monthly subscriber moving the same plan to yearly is not told it is a downgrade', async () => {
    const wrapper = await mountBilling(subscription())

    await pickInterval(wrapper, 'year')
    expect(buttonLabels(wrapper)).not.toContain(t('subscription.downgrade'))
    await click(wrapper, t('subscription.switchInterval.year'))
    expect(store.switchPlan).toHaveBeenCalledWith(PRO_YEARLY.id)
  })

  test('a picked billing period is remembered, also from the marketing site', async () => {
    const wrapper = await mountBilling(null)
    await pickInterval(wrapper, 'year')

    const again = await mountBilling(null)
    expect(options(again, t('subscription.billingInterval'))[1]!.attributes('aria-checked')).toBe(
      'true',
    )

    localStorage.clear()
    window.history.replaceState(null, '', '/settings/billing?interval=year')
    adoptPlanChoiceFromUrl()
    const fromSite = await mountBilling(null)
    await click(fromSite, t('subscription.subscribe'), 1)
    expect(store.checkout).toHaveBeenCalledWith(PRO_YEARLY.id)
  })

  test('with one billing period, there is nothing to pick', async () => {
    const wrapper = await mountBilling(null, [
      plan(1, 'Free', [FREE]),
      plan(3, 'Business', [BUSINESS]),
    ])

    expect(intervalOptions(wrapper)).toHaveLength(0)
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
